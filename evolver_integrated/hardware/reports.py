"""Persistent commissioning reports; prior reports are never overwritten."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .model import HardwareTestResult, TestStatus


def aggregate(results: list[HardwareTestResult]) -> str:
    statuses = {result.status for result in results}
    if TestStatus.FAIL in statuses:
        return "fail"
    if TestStatus.WARN in statuses:
        return "pass_with_warnings"
    return "pass"


def write_report(path: Path, device: dict[str, Any], operator: str, results: list[HardwareTestResult], commissioning: bool = False) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        path = path.with_name(f"{path.stem}-{stamp}{path.suffix}")
    now = datetime.now(timezone.utc).isoformat()
    payload = {"schema_version": 1, "device": device, "commissioning": {"started_at": now, "completed_at": now, "operator": operator, "result": aggregate(results), "guided": commissioning}, "tests": {result.id: result.to_dict() for result in results}, "calibration": {"temperature": TestStatus.NOT_CALIBRATED.value, "od": TestStatus.NOT_CALIBRATED.value, "pumps": TestStatus.NOT_CALIBRATED.value}}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def read_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())
