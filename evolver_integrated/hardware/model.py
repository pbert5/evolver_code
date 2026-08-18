"""Typed data shared by command-line, TUI, and future hardwared clients."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class TestStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"
    NOT_TESTABLE = "not_testable"
    NOT_CALIBRATED = "not_calibrated"


@dataclass
class HardwareTestResult:
    id: str
    component: str
    status: TestStatus
    expected: str
    channel: Optional[int] = None
    observed: Optional[str] = None
    automatic: bool = True
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    duration_ms: int = 0
    debug: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["status"] = self.status.value
        return result


HARDWARE_MAP = {
    "sleeves": {
        0: {"thermistor_pin": "A0", "photodiode_pin": "A2", "heater_pin": 2, "od_led_pin": 4, "stir_pin": 11},
        1: {"thermistor_pin": "A1", "photodiode_pin": "A3", "heater_pin": 3, "od_led_pin": 5, "stir_pin": 13},
    },
    "pumps": {0: 6, 1: 7, 2: 8, 3: 9, 4: 10, 5: 12},
}
