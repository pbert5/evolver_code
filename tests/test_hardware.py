from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from evolver_integrated.hardware.fake import FakeHardwareBackend
from evolver_integrated.hardware.model import HardwareTestResult, TestStatus
from evolver_integrated.hardware.protocol import (parse_hardware_reply, parse_identity,
                                                  pulse_heater_command, pulse_pump_command,
                                                  pulse_stir_command, read_thermistor_command,
                                                  set_od_led_command)
from evolver_integrated.hardware.reports import aggregate, read_report, write_report
from evolver_integrated.hardware.service import HardwareTester, discover_ports


def test_firmware_upload_compiles_with_vendored_libraries(monkeypatch):
    from evolver_integrated.hardware import firmware

    commands = []

    def fake_run(command, check=False):
        commands.append(command)

    class FakeSerial:
        def __init__(self, *args, **kwargs): self.replies = iter((
            b"MEV|2|BLANK|1|HELLO|type=minievolver,proto=2,fw=0.2,hw_proto=1,id=BLANK,owner=BLANK|66\n",
            b"HW|1|OK|STATUS|sleeves=2,pumps=6,fw=0.2,id=BLANK,hw_proto=1\n",
            b"HW|1|OK|SAFE|outputs=off\n",
        ))
        def __enter__(self): return self
        def __exit__(self, *args): return None
        def write(self, payload): return len(payload)
        def readline(self): return next(self.replies)

    monkeypatch.setattr(firmware.subprocess, "run", fake_run)
    monkeypatch.setattr(firmware.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(firmware, "glob", lambda pattern: ["/dev/ttyACM9"])
    monkeypatch.setitem(sys.modules, "serial", SimpleNamespace(Serial=FakeSerial))

    assert firmware.main(["upload", "--port", "/dev/ttyACM9"]) == 0
    command = commands[-1]
    assert command[command.index("compile") + 1:] == [
        "--fqbn", firmware.FQBN, "--libraries", "evolver-arduino/libraries",
        "--port", "/dev/ttyACM9", "--upload", "evolver-arduino/SAMD21/MINEVOLVER",
    ]
    assert "upload" not in command


def test_actuator_prompt_repeats_with_a_longer_bounded_pulse():
    from evolver_integrated.hardware.cli import _test_actuator

    class FakeTester:
        def __init__(self): self.durations = []

        def actuator(self, kind, channel, duration_ms):
            self.durations.append(duration_ms)
            return HardwareTestResult("pump.0.actuation", kind, TestStatus.NOT_TESTABLE, "x", channel=channel)

        def repeat_actuator(self, result, kind, channel, duration_ms):
            self.durations.append(duration_ms)
            return True

        def record_observation(self, result, observed_channel):
            result.status = TestStatus.PASS if observed_channel == result.channel else TestStatus.FAIL
            return result

    tester = FakeTester()
    answers = iter((" ", "0"))
    result = _test_actuator(tester, "pump", 0, lambda prompt: next(answers))
    assert tester.durations == [250, 500]
    assert result.status == TestStatus.PASS


def test_pump_direction_calibration_records_shared_direction():
    from evolver_integrated.hardware.cli import _calibrate_pump_direction, _summarize_pump_directions

    class FakeTester:
        def __init__(self): self.results, self.durations = [], []
        def pump_direction(self, channel, duration_ms):
            self.durations.append(duration_ms)
            result = HardwareTestResult(f"pump.{channel}.direction", "pump_direction", TestStatus.NOT_TESTABLE, "x", channel=channel, debug={})
            self.results.append(result)
            return result
        def repeat_pump_direction(self, result, channel, duration_ms): self.durations.append(duration_ms); return True
        def calibration_summary(self, status, observed, debug):
            result = HardwareTestResult("pump.direction.calibration", "pump_direction", status, "x", observed=observed, debug=debug)
            self.results.append(result)
            return result

    tester = FakeTester()
    for channel in range(6):
        assert _calibrate_pump_direction(tester, channel, lambda prompt: "CCW").observed == "counterclockwise"
    summary = _summarize_pump_directions(tester)
    assert summary.status == TestStatus.PASS
    assert summary.debug == {"mode": "shared", "direction": "counterclockwise"}


def test_pump_direction_calibration_records_mixed_directions_per_pump():
    from evolver_integrated.hardware.cli import _summarize_pump_directions

    class FakeTester:
        def __init__(self):
            self.results = [
                HardwareTestResult(f"pump.{channel}.direction", "pump_direction", TestStatus.PASS, "x", channel=channel,
                                   observed="clockwise" if channel % 2 else "counterclockwise")
                for channel in range(6)
            ]
        def calibration_summary(self, status, observed, debug):
            return HardwareTestResult("pump.direction.calibration", "pump_direction", status, "x", observed=observed, debug=debug)

    summary = _summarize_pump_directions(FakeTester())
    assert summary.status == TestStatus.WARN
    assert summary.debug["mode"] == "per_pump"
    assert summary.debug["directions"] == {0: "counterclockwise", 1: "clockwise", 2: "counterclockwise", 3: "clockwise", 4: "counterclockwise", 5: "clockwise"}


def test_protocol_identity_parsing():
    identity = parse_identity("MEV|2|BLANK|1|HELLO|type=minievolver,proto=2,fw=0.2,hw_proto=1,id=BLANK,owner=BLANK|66")
    assert identity.device_id == "BLANK" and identity.hw_protocol == 1


@pytest.mark.parametrize("command", [read_thermistor_command(0), set_od_led_command(1, 128), pulse_pump_command(5, 1000), pulse_stir_command(1, 500, 100), pulse_heater_command(0, 250, 32)])
def test_command_generation(command: str): assert command.endswith("_!") and command.startswith("HW_")


@pytest.mark.parametrize("factory", [lambda: pulse_pump_command(6, 1), lambda: pulse_heater_command(0, 251, 1), lambda: set_od_led_command(2, 1)])
def test_command_limits(factory):
    with pytest.raises(ValueError): factory()


def test_hardware_reply_success_error_and_malformed():
    assert parse_hardware_reply("HW|1|OK|THERMISTOR|channel=0,value=31284", "THERMISTOR").fields["value"] == "31284"
    with pytest.raises(ValueError, match="invalid_channel"): parse_hardware_reply("HW|1|ERR|PULSE_PUMP|reason=invalid_channel")
    with pytest.raises(ValueError): parse_hardware_reply("OK")


def test_status_parses_safe_idle_fields():
    reply = parse_hardware_reply(
        "HW|1|OK|STATUS|sleeves=2,pumps=6,fw=0.2,hw_proto=1,"
        "temp_control=off,mode=idle",
        "STATUS",
    )
    assert reply.fields["temp_control"] == "off"
    assert reply.fields["mode"] == "idle"


def test_protocol_rejects_non_evolver():
    with pytest.raises(ValueError, match="not a min-eVOLVER"): parse_identity("hello")


def test_safe_state_runs_after_exception_and_ctrl_c_equivalent():
    backend = FakeHardwareBackend(); tester = HardwareTester(backend)
    with pytest.raises(KeyboardInterrupt):
        with tester.session(): raise KeyboardInterrupt()
    assert any(item["tx"] == "HW_SAFE_!" for item in backend.debug_log)
    assert not backend.opened


def test_stable_thermistor_is_plausible():
    backend = FakeHardwareBackend(); tester = HardwareTester(backend)
    assert tester.sensor(0)[0].status == TestStatus.PASS


def test_rail_thermistor_warns():
    backend = FakeHardwareBackend(responses={"HW_READ_THERMISTOR": "HW|1|OK|THERMISTOR|channel=0,value=0"})
    assert HardwareTester(backend).sensor(0)[0].status == TestStatus.WARN


def test_all_near_rail_sleeve_inputs_suggest_unplugged_connectors():
    backend = FakeHardwareBackend(responses={
        "HW_READ_THERMISTOR": "HW|1|OK|THERMISTOR|channel=0,value=65520",
        "HW_READ_PHOTODIODE": "HW|1|OK|PHOTODIODE|channel=0,value=65520",
    })
    tester = HardwareTester(backend)
    for channel in range(2):
        tester.sensor(channel)
        tester.od(channel)
    warning_ids = {result.id for result in tester.analog_connection_warnings()}
    assert {"sleeve.0.connection", "sleeve.1.connection", "sleeves.thermistor_connection", "sleeves.photodiode_connection", "sleeves.analog_connection"} <= warning_ids


def test_one_near_rail_sleeve_suggests_that_bioreactor_is_unplugged():
    tester = HardwareTester(FakeHardwareBackend())
    tester.analog_readings = {
        "thermistor.0": [65520], "photodiode.0": [65520],
        "thermistor.1": [32000], "photodiode.1": [20000],
    }
    warnings = tester.analog_connection_warnings()
    assert warnings[0].id == "sleeve.0.connection"
    assert "bioreactor/Sleeve may be unplugged" in warnings[0].observed


def test_od_channel_association():
    backend = FakeHardwareBackend(); values = iter([100, 100, 120, 101, 170, 103, 230, 104])
    backend.responses["HW_READ_PHOTODIODE"] = "HW|1|OK|PHOTODIODE|channel=0,value=200"
    # The service's response parser is exercised separately; this verifies the failure-safe OD sequence.
    results = HardwareTester(backend).od(0)
    assert any(result.id.endswith("od_calibration") for result in results)


def test_unsupported_hardware_protocol_fails():
    backend = FakeHardwareBackend()
    backend.identity = lambda: parse_identity("MEV|2|OLD|1|HELLO|type=minievolver,proto=2,fw=0.1,id=OLD|00")
    assert HardwareTester(backend).protocol().status == TestStatus.FAIL


def test_duplicate_mapping_warning():
    tester = HardwareTester(FakeHardwareBackend())
    tester._result("pump.0.actuation", "pump", TestStatus.PASS, "x", channel=0, observed="physical channel 1")
    tester._result("pump.1.actuation", "pump", TestStatus.PASS, "x", channel=1, observed="physical channel 1")
    assert tester.duplicate_mapping_warnings()[0].status == TestStatus.WARN


def test_result_report_and_non_overwrite(tmp_path: Path):
    result = HardwareTestResult("controller.usb", "controller", TestStatus.PASS, "USB")
    first = write_report(tmp_path / "report.json", {"id": "FAKE"}, "tester", [result], True)
    second = write_report(tmp_path / "report.json", {"id": "FAKE"}, "tester", [result], True)
    assert first != second and read_report(first)["tests"]["controller.usb"]["status"] == "pass" and aggregate([result]) == "pass"


def test_explicit_port_discovery(): assert discover_ports("/dev/ttyACM9") == ["/dev/ttyACM9"]
