"""Deterministic backend for CI and TUI tests; it never opens real hardware."""
from __future__ import annotations

from .protocol import DeviceIdentity


class FakeHardwareBackend:
    def __init__(self, port: str = "/dev/ttyACM-fake", responses: dict[str, str] | None = None) -> None:
        self.port, self.responses = port, responses or {}
        self.debug_log: list[dict] = []
        self.opened = False

    def open(self) -> None: self.opened = True
    def close(self) -> None: self.opened = False
    def identity(self) -> DeviceIdentity:
        return DeviceIdentity(2, "FAKE-001", "0.1", "minievolver", "MEV|2|FAKE-001|1|HELLO|type=minievolver,proto=2,fw=0.1,id=FAKE-001")
    def command(self, name: str, **arguments: object) -> str:
        response = self.responses.get(name, "OK")
        self.debug_log.append({"tx": name, "arguments": arguments, "rx": response})
        return response
