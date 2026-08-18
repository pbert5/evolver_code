"""Safe, transport-neutral min-eVOLVER commissioning service."""
from __future__ import annotations

import glob
import time
from contextlib import contextmanager
from typing import Iterator, Optional, Protocol

from .model import HARDWARE_MAP, HardwareTestResult, TestStatus
from .protocol import (HANDSHAKE, HW_PROTOCOL_VERSION, DeviceIdentity, HardwareReply,
                       hw_safe_command, hw_status_command, parse_hardware_reply,
                       parse_identity, pulse_heater_command, pulse_pump_command,
                       pulse_stir_command, read_photodiode_command,
                       read_thermistor_command, set_od_led_command)


class HardwareError(RuntimeError): pass


class HardwareBackend(Protocol):
    port: str
    debug_log: list[dict]
    def open(self) -> None: ...
    def close(self) -> None: ...
    def identity(self) -> DeviceIdentity: ...
    def exchange(self, payload: str) -> str: ...


class CommissioningBackend:
    """Typed adapter; UI code never assembles serial strings."""
    def _hw(self, payload: str, operation: str) -> HardwareReply:
        return parse_hardware_reply(self.exchange(payload), operation)
    def hw_status(self) -> HardwareReply: return self._hw(hw_status_command(), "STATUS")
    def safe_state(self) -> HardwareReply: return self._hw(hw_safe_command(), "SAFE")
    def read_thermistor(self, channel: int) -> int: return int(self._hw(read_thermistor_command(channel), "THERMISTOR").fields["value"])
    def read_photodiode(self, channel: int) -> int: return int(self._hw(read_photodiode_command(channel), "PHOTODIODE").fields["value"])
    def set_od_led(self, channel: int, level: int) -> HardwareReply: return self._hw(set_od_led_command(channel, level), "SET_OD_LED")
    def pulse_pump(self, channel: int, duration_ms: int) -> HardwareReply: return self._hw(pulse_pump_command(channel, duration_ms), "PULSE_PUMP")
    def pulse_stir(self, channel: int, duration_ms: int, level: int) -> HardwareReply: return self._hw(pulse_stir_command(channel, duration_ms, level), "PULSE_STIR")
    def pulse_heater(self, channel: int, duration_ms: int, level: int) -> HardwareReply: return self._hw(pulse_heater_command(channel, duration_ms, level), "PULSE_HEATER")


class LocalSerialBackend(CommissioningBackend):
    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 2.0) -> None:
        self.port, self.baudrate, self.timeout, self.serial = port, baudrate, timeout, None
        self.debug_log: list[dict] = []
    def open(self) -> None:
        try:
            import serial
            self.serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        except ImportError as exc: raise HardwareError("pyserial is required; enter the Nix development shell") from exc
        except Exception as exc: raise HardwareError(f"could not open {self.port}: {exc}") from exc
    def close(self) -> None:
        if self.serial is not None: self.serial.close(); self.serial = None
    def exchange(self, payload: str) -> str:
        if self.serial is None: raise HardwareError("serial port is not open")
        started = time.monotonic(); self.serial.write((payload + "\n").encode()); self.serial.flush()
        reply = self.serial.readline().decode(errors="replace").strip()
        self.debug_log.append({"tx": payload, "rx": reply, "duration_ms": round((time.monotonic() - started) * 1000)})
        if not reply: raise HardwareError(f"timeout waiting for response to {payload}")
        return reply
    def identity(self) -> DeviceIdentity: return parse_identity(self.exchange(HANDSHAKE))


def discover_ports(port: Optional[str] = None) -> list[str]: return [port] if port else sorted(glob.glob("/dev/ttyACM*"))


class HardwareTester:
    def __init__(self, backend: HardwareBackend) -> None: self.backend, self.results = backend, []
    def _result(self, ident: str, component: str, status: TestStatus, expected: str, **kwargs: object) -> HardwareTestResult:
        result = HardwareTestResult(ident, component, status, expected, debug={"port": self.backend.port, **kwargs.pop("debug", {})}, **kwargs); self.results.append(result); return result
    @contextmanager
    def session(self) -> Iterator["HardwareTester"]:
        self.backend.open()
        try: yield self
        finally:
            try: self.safe_state()
            finally: self.backend.close()
    def safe_state(self) -> HardwareTestResult:
        try:
            response = self.backend.safe_state()  # type: ignore[attr-defined]
            return self._result("safety.shutdown", "safety", TestStatus.PASS, "all outputs off", observed="safe state acknowledged", debug={"response": response.raw})
        except Exception as exc: return self._result("safety.shutdown", "safety", TestStatus.WARN, "all outputs off", observed="could not confirm shutdown; disconnect actuator power", debug={"error": str(exc)})
    def usb(self) -> HardwareTestResult: return self._result("controller.usb", "controller", TestStatus.PASS, "readable USB serial device", observed=self.backend.port)
    def protocol(self) -> HardwareTestResult:
        try:
            identity = self.backend.identity()
            if identity.hw_protocol < HW_PROTOCOL_VERSION: raise HardwareError("Connected min-eVOLVER firmware does not implement hw_proto>=1. Flash the commissioning-enabled firmware first.")
            status = self.backend.hw_status()  # type: ignore[attr-defined]
            return self._result("controller.protocol", "controller", TestStatus.PASS, "protocol 2 min-eVOLVER with hw_proto>=1", observed=f"{identity.device_id} firmware {identity.firmware}", debug={"identity": identity.raw, "status": status.raw})
        except Exception as exc: return self._result("controller.protocol", "controller", TestStatus.FAIL, "WHO_ARE_YOU_! and HW_STATUS", observed=str(exc))
    def sensor(self, sleeve: int) -> list[HardwareTestResult]:
        try:
            samples = [self.backend.read_thermistor(sleeve) for _ in range(3)]  # type: ignore[attr-defined]
            plausible = all(1 <= value <= 65534 for value in samples) and max(samples) - min(samples) < 5000
            electronic = self._result(f"sleeve.{sleeve}.thermistor", "thermistor", TestStatus.PASS if plausible else TestStatus.WARN, f"thermistor on {HARDWARE_MAP['sleeves'][sleeve]['thermistor_pin']}", observed=str(samples))
        except Exception as exc: electronic = self._result(f"sleeve.{sleeve}.thermistor", "thermistor", TestStatus.FAIL, "three thermistor readings", observed=str(exc))
        return [electronic, self._result(f"sleeve.{sleeve}.temperature_calibration", "temperature", TestStatus.NOT_CALIBRATED, "calibrated temperature", automatic=False)]
    def od(self, sleeve: int) -> list[HardwareTestResult]:
        try:
            self.backend.set_od_led(0, 0); self.backend.set_od_led(1, 0)  # type: ignore[attr-defined]
            baseline = [self.backend.read_photodiode(i) for i in range(2)]  # type: ignore[attr-defined]
            readings = []
            for level in (32, 128, 255):
                self.backend.set_od_led(sleeve, level)  # type: ignore[attr-defined]
                readings.append([self.backend.read_photodiode(i) for i in range(2)])  # type: ignore[attr-defined]
            self.backend.set_od_led(sleeve, 0)  # type: ignore[attr-defined]
            own = [row[sleeve] - baseline[sleeve] for row in readings]; other = [row[1 - sleeve] - baseline[1 - sleeve] for row in readings]
            drive = max(abs(value) for value in own); cross = max(abs(value) for value in other)
            meaningful = 5 <= drive and drive > cross
            return [self._result(f"sleeve.{sleeve}.od_led_drive", "od_led", TestStatus.PASS, "independent LED PWM drive", observed=str(readings), debug={"baseline": baseline}), self._result(f"sleeve.{sleeve}.photodiode_response", "photodiode", TestStatus.PASS if meaningful else TestStatus.WARN, "non-rail, meaningful associated response", observed=str(own)), self._result(f"sleeve.{sleeve}.channel_association", "photodiode", TestStatus.PASS if meaningful else TestStatus.WARN, "associated response exceeds cross-channel response", observed=f"associated={own}, cross={other}"), self._result(f"sleeve.{sleeve}.od_calibration", "od", TestStatus.NOT_CALIBRATED, "calibrated OD", automatic=False)]
        except Exception as exc:
            return [self._result(f"sleeve.{sleeve}.od", "od", TestStatus.FAIL, "OD LED/photodiode sequence", observed=str(exc))]
        finally:
            try: self.backend.set_od_led(sleeve, 0)  # type: ignore[attr-defined]
            except Exception: pass
    def actuator(self, kind: str, channel: int, duration_ms: int = 500) -> HardwareTestResult:
        pin = HARDWARE_MAP["pumps"][channel] if kind == "pump" else HARDWARE_MAP["sleeves"][channel][f"{kind}_pin"]
        try:
            if kind == "pump": reply = self.backend.pulse_pump(channel, duration_ms)  # type: ignore[attr-defined]
            elif kind == "stir": reply = self.backend.pulse_stir(channel, duration_ms, 100)  # type: ignore[attr-defined]
            else: reply = self.backend.pulse_heater(channel, duration_ms, 32)  # type: ignore[attr-defined]
            return self._result(f"{kind}.{channel}.actuation", kind, TestStatus.NOT_TESTABLE, f"physical {kind} {channel} actuates on pin {pin}", channel=channel, automatic=False, observed="awaiting operator confirmation", debug={"mcu_pin": pin, "response": reply.raw})
        except Exception as exc: return self._result(f"{kind}.{channel}.actuation", kind, TestStatus.FAIL, f"{kind} command acknowledged", channel=channel, observed=str(exc), debug={"mcu_pin": pin})
    def record_observation(self, result: HardwareTestResult, observed_channel: Optional[int]) -> HardwareTestResult:
        result.observed = "none" if observed_channel is None else f"physical channel {observed_channel}"; result.status = TestStatus.PASS if observed_channel == result.channel else TestStatus.FAIL; return result
    def duplicate_mapping_warnings(self) -> list[HardwareTestResult]:
        seen, warnings = {}, []
        for result in self.results:
            if result.component not in ("pump", "stir") or result.status != TestStatus.PASS or not result.observed: continue
            if result.observed in seen: warnings.append(self._result(f"{result.component}.mapping.duplicate", result.component, TestStatus.WARN, "unique physical mapping", observed=f"{result.observed} also reported by {seen[result.observed].id}"))
            else: seen[result.observed] = result
        return warnings
