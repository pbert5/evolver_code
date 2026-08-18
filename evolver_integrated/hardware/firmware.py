"""Reproducible Arduino CLI workflow using a workspace-local core data directory."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

FQBN = "SparkFun:samd:samd21_mini"
CORES = ("arduino:samd", "sparkfun:samd")


def _source() -> Path:
    return Path(os.environ.get("EVOLVER_FIRMWARE_DIR", "SAMD21/MINEVOLVER"))


def _cli() -> list[str]:
    data = Path(os.environ.get("EVOLVER_ARDUINO_DATA", ".arduino-cli"))
    data.mkdir(parents=True, exist_ok=True)
    return ["arduino-cli", "--config-file", str(data / "arduino-cli.yaml")]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("setup", "build", "upload"))
    parser.add_argument("--port")
    args = parser.parse_args(argv)
    if args.action == "setup":
        for core in CORES:
            subprocess.run(_cli() + ["core", "install", core], check=True)
        return 0
    source = _source()
    if not source.joinpath("MINEVOLVER.ino").is_file():
        print("Firmware source SAMD21/MINEVOLVER/MINEVOLVER.ino is not present in this checkout. Restore/initialize the evolver-arduino source (or set EVOLVER_FIRMWARE_DIR) before building.", file=sys.stderr)
        return 2
    command = _cli() + (["compile", "--fqbn", FQBN, str(source)] if args.action == "build" else ["upload", "--fqbn", FQBN, "--port", args.port or "/dev/ttyACM0", str(source)])
    subprocess.run(command, check=True)
    return 0


if __name__ == "__main__": raise SystemExit(main())
