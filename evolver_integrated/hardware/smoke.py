"""Opt-in, non-actuating live commissioning protocol smoke test."""
from __future__ import annotations

import argparse
import sys

from .service import HardwareTester, LocalSerialBackend


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hardware-smoke")
    parser.add_argument("--port", required=True)
    args = parser.parse_args(argv)
    tester = HardwareTester(LocalSerialBackend(args.port))
    try:
        with tester.session():
            tester.protocol()
            for channel in range(2):
                tester.sensor(channel)
                tester.backend.read_photodiode(channel)  # type: ignore[attr-defined]
    except Exception as exc:
        print(f"Hardware smoke test failed safely: {exc}", file=sys.stderr)
        return 2
    for result in tester.results:
        print(f"{result.status.value}: {result.id} {result.observed or ''}")
    return 1 if any(result.status.value == "fail" for result in tester.results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
