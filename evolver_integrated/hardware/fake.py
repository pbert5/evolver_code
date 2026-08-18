"""Deterministic backend for CI and TUI tests; it never opens real hardware."""
from __future__ import annotations

from .protocol import DeviceIdentity
from .service import CommissioningBackend


class FakeHardwareBackend(CommissioningBackend):
    def __init__(self, port: str = "/dev/ttyACM-fake", responses: dict[str, str] | None = None) -> None:
        self.port, self.responses = port, responses or {}
        self.debug_log: list[dict] = []
        self.opened = False

    def open(self) -> None: self.opened = True
    def close(self) -> None: self.opened = False
    def identity(self) -> DeviceIdentity:
        return DeviceIdentity(2, "FAKE-001", "0.2", "minievolver", 1, "MEV|2|FAKE-001|1|HELLO|type=minievolver,proto=2,fw=0.2,hw_proto=1,id=FAKE-001")
    def exchange(self, payload: str) -> str:
        operation = payload.split(",", 1)[0].removesuffix("_!")
        defaults = {
            "HW_SAFE": "HW|1|OK|SAFE|outputs=off",
            "HW_STATUS": "HW|1|OK|STATUS|sleeves=2,pumps=6,hw_proto=1",
            "HW_READ_THERMISTOR": "HW|1|OK|THERMISTOR|channel=0,value=32000",
            "HW_READ_PHOTODIODE": "HW|1|OK|PHOTODIODE|channel=0,value=20000",
            "HW_SET_OD_LED": "HW|1|OK|SET_OD_LED|channel=0,pin=4,level=0",
            "HW_PULSE_PUMP": "HW|1|OK|PULSE_PUMP|channel=0,pin=6,duration_ms=500",
            "HW_PULSE_STIR": "HW|1|OK|PULSE_STIR|channel=0,pin=11,duration_ms=500,level=100",
            "HW_PULSE_HEATER": "HW|1|OK|PULSE_HEATER|channel=0,pin=2,duration_ms=250,level=32",
        }
        response = self.responses.get(payload, self.responses.get(operation, defaults[operation]))
        self.debug_log.append({"tx": payload, "rx": response})
        return response
