"""``hardware-test`` command.  This is intentionally not commissioning."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable

from .model import HardwareTestResult, TestStatus
from .reports import write_report
from .service import HardwareError, HardwareTester, LocalSerialBackend, discover_ports


COMMANDS = ("usb", "firmware", "protocol", "sensors", "od", "stir", "pumps", "pump-direction", "heaters", "all")
PULSE_PROFILES = {"pump": (250, 250, 1000), "stir": (250, 250, 1000), "heater": (100, 50, 250)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hardware-test", description="Dry-safe min-eVOLVER hardware tests")
    parser.add_argument("command", choices=COMMANDS)
    parser.add_argument("--port")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--wet", action="store_true", help="reserved; closed-loop wet heater tests require firmware support")
    return parser


def _print(results: list[HardwareTestResult], as_json: bool, debug: bool) -> None:
    if as_json:
        print(json.dumps([result.to_dict() for result in results], indent=2))
        return
    print("eVOLVER Hardware Test")
    for result in results:
        print(f"[{result.status.value.upper():15}] {result.id}\n       expected: {result.expected}")
        if result.observed: print(f"       observed: {result.observed}")
        if debug and result.debug: print(f"       debug: {json.dumps(result.debug, sort_keys=True)}")


def _test_actuator(tester: HardwareTester, kind: str, channel: int, confirm: Callable[[str], str]) -> HardwareTestResult:
    duration_ms, increment_ms, maximum_ms = PULSE_PROFILES[kind]
    result = tester.actuator(kind, channel, duration_ms)
    while result.status != TestStatus.FAIL:
        answer = confirm(f"Logical {kind} {channel} pulsed for {duration_ms} ms; which physical channel moved? (number/N/S; Enter or Space=re-pulse): ")
        value = answer.strip().lower()
        if not value:
            duration_ms = min(duration_ms + increment_ms, maximum_ms)
            if not tester.repeat_actuator(result, kind, channel, duration_ms): break
        elif value == "s":
            result.status = TestStatus.SKIP
            break
        elif value == "n":
            tester.record_observation(result, None)
            break
        elif value.isdigit():
            tester.record_observation(result, int(value))
            break
    return result


_PUMP_DIRECTIONS = {
    "c": "clockwise", "cw": "clockwise", "clockwise": "clockwise",
    "ccw": "counterclockwise", "counterclockwise": "counterclockwise", "counter-clockwise": "counterclockwise",
}


def _calibrate_pump_direction(tester: HardwareTester, channel: int, confirm: Callable[[str], str]) -> HardwareTestResult:
    """Record the rotation direction, viewed from the pump drive-shaft side."""
    duration_ms, increment_ms, maximum_ms = PULSE_PROFILES["pump"]
    result = tester.pump_direction(channel, duration_ms)
    while result.status != TestStatus.FAIL:
        answer = confirm(
            f"Logical pump {channel} pulsed for {duration_ms} ms; viewed from the drive-shaft side, "
            "direction? (C=clockwise/CCW=counterclockwise/N/S; Enter or Space=re-pulse): "
        )
        value = answer.strip().lower()
        if not value:
            duration_ms = min(duration_ms + increment_ms, maximum_ms)
            if not tester.repeat_pump_direction(result, channel, duration_ms): break
        elif value == "s":
            result.status = TestStatus.SKIP
            result.observed = "direction not recorded"
            break
        elif value == "n":
            result.status = TestStatus.FAIL
            result.observed = "no rotation observed"
            break
        elif value in _PUMP_DIRECTIONS:
            result.status = TestStatus.PASS
            result.observed = _PUMP_DIRECTIONS[value]
            result.debug["direction"] = result.observed
            result.debug["viewpoint"] = "drive-shaft side"
            break
    return result


def _summarize_pump_directions(tester: HardwareTester) -> HardwareTestResult | None:
    directions = {result.channel: result.observed for result in tester.results
                  if result.component == "pump_direction" and result.status == TestStatus.PASS and result.channel is not None}
    if len(directions) != 6:
        return None
    values = set(directions.values())
    if len(values) == 1:
        direction = next(iter(values))
        return tester.calibration_summary(TestStatus.PASS, f"all six pumps: {direction}", {"mode": "shared", "direction": direction})
    mapping = ", ".join(f"{channel}={directions[channel]}" for channel in sorted(directions))
    return tester.calibration_summary(TestStatus.WARN, f"per-pump directions: {mapping}", {"mode": "per_pump", "directions": directions})


def run(args: argparse.Namespace, confirm: Callable[[str], str] = input) -> list[HardwareTestResult]:
    candidates = discover_ports(args.port)
    if not candidates:
        raise HardwareError("no /dev/ttyACM* ports found; use --port if the device has another name")
    if len(candidates) > 1 and not args.port:
        raise HardwareError("multiple ACM devices found; choose one with --port: " + ", ".join(candidates))
    tester = HardwareTester(LocalSerialBackend(candidates[0]))
    with tester.session():
        selected = args.command
        if selected in ("usb", "all"): tester.usb()
        if selected in ("protocol", "firmware", "all"): tester.protocol()
        if selected in ("sensors", "all"):
            for channel in range(2): tester.sensor(channel)
        if selected in ("od", "all"):
            for channel in range(2): tester.od(channel)
        tester.analog_connection_warnings()
        for group, kind, channels in (("pumps", "pump", range(6)), ("stir", "stir", range(2)), ("heaters", "heater", range(2))):
            if selected in (group, "all"):
                for channel in channels:
                    _test_actuator(tester, kind, channel, confirm)
        if selected == "pump-direction":
            for channel in range(6):
                _calibrate_pump_direction(tester, channel, confirm)
            _summarize_pump_directions(tester)
        tester.duplicate_mapping_warnings()
    return tester.results


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        results = run(args)
    except (HardwareError, KeyboardInterrupt) as exc:
        print(f"Hardware test failed safely: {exc}", file=sys.stderr)
        return 2
    _print(results, args.as_json, args.debug)
    if args.report:
        destination = write_report(args.report, {"port": args.port or "auto", "type": "minievolver"}, "hardware-test", results)
        print(f"Report: {destination}")
    return 1 if any(result.status == TestStatus.FAIL for result in results) else 0


if __name__ == "__main__": raise SystemExit(main())
