from pathlib import Path

from evolver_integrated.hardware.fake import FakeHardwareBackend
from evolver_integrated.hardware.model import HardwareTestResult, TestStatus
from evolver_integrated.hardware.protocol import parse_identity
from evolver_integrated.hardware.reports import aggregate, read_report, write_report
from evolver_integrated.hardware.service import HardwareTester, discover_ports


def test_protocol_identity_parsing():
    identity = parse_identity("MEV|2|BLANK|1|HELLO|type=minievolver,proto=2,fw=0.1,id=BLANK,owner=BLANK|66")
    assert identity.protocol == 2
    assert identity.device_id == "BLANK"


def test_protocol_rejects_non_evolver():
    try:
        parse_identity("hello")
    except ValueError as exc:
        assert "not a min-eVOLVER" in str(exc)
    else:
        assert False


def test_safe_state_runs_after_exception():
    backend = FakeHardwareBackend()
    tester = HardwareTester(backend)
    try:
        with tester.session():
            raise RuntimeError("test fault")
    except RuntimeError:
        pass
    assert any(item["tx"] == "SAFE_STATE" for item in backend.debug_log)
    assert not backend.opened


def test_duplicate_mapping_warning():
    tester = HardwareTester(FakeHardwareBackend())
    a = tester._result("pump.0.actuation", "pump", TestStatus.PASS, "x", channel=0, observed="physical channel 1")
    b = tester._result("pump.1.actuation", "pump", TestStatus.PASS, "x", channel=1, observed="physical channel 1")
    assert tester.duplicate_mapping_warnings()[0].status == TestStatus.WARN


def test_result_report_and_non_overwrite(tmp_path: Path):
    result = HardwareTestResult("controller.usb", "controller", TestStatus.PASS, "USB")
    first = write_report(tmp_path / "report.json", {"id": "FAKE"}, "tester", [result], True)
    second = write_report(tmp_path / "report.json", {"id": "FAKE"}, "tester", [result], True)
    assert first != second
    assert read_report(first)["tests"]["controller.usb"]["status"] == "pass"
    assert aggregate([result]) == "pass"


def test_explicit_port_discovery():
    assert discover_ports("/dev/ttyACM9") == ["/dev/ttyACM9"]
