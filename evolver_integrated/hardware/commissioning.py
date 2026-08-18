"""Guided commissioning orchestration; it calls the test layer, never copies it."""
from __future__ import annotations

import argparse
from pathlib import Path

from .cli import build_parser as hardware_parser, run as run_hardware
from .reports import read_report, write_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="commission-evolver", description="Guided min-eVOLVER commissioning")
    parser.add_argument("--skip-flash", action="store_true")
    parser.add_argument("--skip-heaters", action="store_true")
    parser.add_argument("--port")
    parser.add_argument("--device-id")
    parser.add_argument("--operator", required=True)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--report", type=Path, default=Path("commissioning/report.json"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.resume:
        prior = read_report(args.resume)
        print(f"Resuming record for {prior.get('device', {}).get('id', 'unknown device')}; completed tests are retained in the prior report.")
    if not args.skip_flash:
        print("Firmware flash is a separate explicit step. Run `nix run .#upload-firmware -- --port ...`, then re-run with --skip-flash.")
        return 2
    if input("This will actuate dry hardware. Continue? [y/N] ").strip().lower() != "y":
        print("Commissioning cancelled; no outputs were actuated.")
        return 0
    hw_args = hardware_parser().parse_args(["all", "--port", args.port] if args.port else ["all"])
    results = run_hardware(hw_args)
    if args.skip_heaters:
        results = [r for r in results if r.component != "heater"]
    report = write_report(args.report, {"type": "minievolver", "id": args.device_id or "unknown", "port": args.port or "auto"}, args.operator, results, commissioning=True)
    print(f"Commissioning report: {report}")
    return 1 if any(r.status.value == "fail" for r in results) else 0


if __name__ == "__main__": raise SystemExit(main())
