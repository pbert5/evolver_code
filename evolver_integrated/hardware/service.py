"""Safe, transport-neutral min-eVOLVER hardware test service.

Protocol command names outside the identity handshake are firmware-version
dependent.  They are centrally located here so protocol adapters can be
updated after the firmware source is restored, rather than leaking commands
into CLI/TUI code.
"""
from __future__ import annotations

import glob
import time
from contextlib import contextmanager
from typing import Iterator, Optional, Protocol

from .model import HARDWARE_MAP, HardwareTestResult, TestStatus
from .protocol import HANDSHAKE, DeviceIdentity, parse_identity


class HardwareError(RuntimeError):
    pass


class HardwareBackend(Protocol):
    port: str
    debug_log: list[dict]
    def open(self) -> None: ...
    def close(self) -> None: ...
    def identity(self) -> DeviceIdentity: ...
    def command(self, name: str, **arguments: object) -> str: ...


class LocalSerialBackend:
    """Direct serial backend for initial bring-up; hardwared should replace it."""
    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 2.0) -> None:
        self.port, self.baudrate, self.timeout = port, baudrate, timeout
        self.serial = None
        self.debug_log: list[dict] = []

    def open(self) -> None:
        try:
            import serial
            self.serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        except ImportError as exc:
            raise HardwareError("pyserial is required; enter the Nix development shell") from exc
        except Exception as exc:
            raise HardwareError(f"could not open {self.port}: {exc}") from exc

    def close(self) -> None:
        if self.serial is not None:
            self.serial.close()
            self.serial = None

    def command(self, name: str, **arguments: object) -> str:
        if self.serial is None:
            raise HardwareError("serial port is not open")
        # The firmware command adapter is the only command construction point.
        payload = name if not arguments else name + "|" + "|".join(str(v) for v in arguments.values())
        started = time.monotonic()
        self.serial.write((payload + "\n").encode())
        self.serial.flush()
        reply = self.serial.readline().decode(errors="replace").strip()
        elapsed = round((time.monotonic() - started) * 1000)
        self.debug_log.append({"tx": payload, "rx": reply, "duration_ms": elapsed})
        if not reply:
            raise HardwareError(f"timeout waiting for response to {name}")
        return reply

    def identity(self) -> DeviceIdentity:
        return parse_identity(self.command(HANDSHAKE))


def discover_ports(port: Optional[str] = None) -> list[str]:
    """Candidate ports; each is later verified with the identity handshake."""
    return [port] if port else sorted(glob.glob("/dev/ttyACM*"))


class HardwareTester:
    def __init__(self, backend: HardwareBackend) -> None:
        self.backend = backend
        self.results: list[HardwareTestResult] = []

    def _result(self, ident: str, component: str, status: TestStatus, expected: str, **kwargs: object) -> HardwareTestResult:
        result = HardwareTestResult(ident, component, status, expected, debug={"port": self.backend.port, **kwargs.pop("debug", {})}, **kwargs)
        self.results.append(result)
        return result

    @contextmanager
    def session(self) -> Iterator["HardwareTester"]:
        self.backend.open()
        try:
            yield self
        finally:
            try:
                self.safe_state()
            finally:
                self.backend.close()

    def safe_state(self) -> HardwareTestResult:
        """Best-effort shutdown, always called from a session finally block."""
        try:
            response = self.backend.command("SAFE_STATE")
            return self._result("safety.shutdown", "safety", TestStatus.PASS, "all pumps, stir, heaters and OD LEDs off", observed="safe state acknowledged", debug={"response": response})
        except Exception as exc:
            return self._result("safety.shutdown", "safety", TestStatus.WARN, "all outputs off", observed="could not confirm shutdown", debug={"error": str(exc)})

    def usb(self) -> HardwareTestResult:
        return self._result("controller.usb", "controller", TestStatus.PASS, "readable USB serial device", observed=self.backend.port)

    def protocol(self) -> HardwareTestResult:
        try:
            identity = self.backend.identity()
            return self._result("controller.protocol", "controller", TestStatus.PASS, "protocol 2 min-eVOLVER", observed=f"{identity.device_id} firmware {identity.firmware}", debug={"response": identity.raw})
        except Exception as exc:
            return self._result("controller.protocol", "controller", TestStatus.FAIL, "WHO_ARE_YOU_! response", observed=str(exc))

    def sensor(self, sleeve: int) -> list[HardwareTestResult]:
        # Adapter names intentionally remain isolated until firmware source is restored.
        try:
            samples = [float(self.backend.command("READ_THERMISTOR", channel=sleeve)) for _ in range(3)]
            plausible = len(set(samples)) > 1 and not any(value in (0, 1023, 65535) for value in samples)
            status = TestStatus.PASS if plausible else TestStatus.WARN
            electronic = self._result(f"sleeve.{sleeve}.thermistor", "thermistor", status, f"thermistor on {HARDWARE_MAP['sleeves'][sleeve]['thermistor_pin']}", observed=str(samples))
        except Exception as exc:
            electronic = self._result(f"sleeve.{sleeve}.thermistor", "thermistor", TestStatus.FAIL, "three thermistor readings", observed=str(exc))
        calibration = self._result(f"sleeve.{sleeve}.temperature_calibration", "temperature", TestStatus.NOT_CALIBRATED, "calibrated temperature", automatic=False)
        return [electronic, calibration]

    def actuator(self, kind: str, channel: int, duration_ms: int = 750) -> HardwareTestResult:
        pin = HARDWARE_MAP["pumps"][channel] if kind == "pump" else HARDWARE_MAP["sleeves"][channel][f"{kind}_pin"]
        try:
            response = self.backend.command("PULSE", component=kind, channel=channel, duration_ms=duration_ms)
            return self._result(f"{kind}.{channel}.actuation", kind, TestStatus.NOT_TESTABLE, f"physical {kind} {channel} actuates on pin {pin}", channel=channel, automatic=False, observed="awaiting operator confirmation", debug={"mcu_pin": pin, "response": response})
        except Exception as exc:
            return self._result(f"{kind}.{channel}.actuation", kind, TestStatus.FAIL, f"{kind} command acknowledged", channel=channel, observed=str(exc), debug={"mcu_pin": pin})

    def record_observation(self, result: HardwareTestResult, observed_channel: Optional[int]) -> HardwareTestResult:
        result.observed = "none" if observed_channel is None else f"physical channel {observed_channel}"
        result.status = TestStatus.PASS if observed_channel == result.channel else TestStatus.FAIL
        return result

    def duplicate_mapping_warnings(self) -> list[HardwareTestResult]:
        seen: dict[str, HardwareTestResult] = {}
        warnings = []
        for result in self.results:
            if result.component not in ("pump", "stir") or result.status != TestStatus.PASS or not result.observed:
                continue
            if result.observed in seen:
                warnings.append(self._result(f"{result.component}.mapping.duplicate", result.component, TestStatus.WARN, "unique physical mapping", observed=f"{result.observed} also reported by {seen[result.observed].id}"))
            else:
                seen[result.observed] = result
        return warnings
