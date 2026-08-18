"""Reproducible Arduino CLI workflow using a workspace-local core data directory."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from glob import glob
from pathlib import Path

FQBN = "SparkFun:samd:samd21_mini"
CORES = ("arduino:samd", "sparkfun:samd")


def _source() -> Path:
    return Path(os.environ.get("EVOLVER_FIRMWARE_DIR", "evolver-arduino/SAMD21/MINEVOLVER"))


def _cli() -> list[str]:
    data = Path(os.environ.get("EVOLVER_ARDUINO_DATA", ".arduino-cli"))
    data.mkdir(parents=True, exist_ok=True)
    return ["arduino-cli", "--config-file", str(data / "arduino-cli.yaml")]


def _verify_commissioning_protocol(port: str) -> str:
    """Find the re-enumerated board and leave it in the firmware safe state."""
    import serial
    from .protocol import parse_hardware_reply, parse_identity

    last_error: Exception | None = None
    for _ in range(10):
        candidates = [port, *(path for path in sorted(glob("/dev/ttyACM*")) if path != port)]
        for candidate in candidates:
            try:
                with serial.Serial(candidate, 9600, timeout=3) as device:
                    device.write(b"WHO_ARE_YOU_!\n")
                    identity = device.readline().decode(errors="replace").strip()
                    device.write(b"HW_STATUS_!\n")
                    status = device.readline().decode(errors="replace").strip()
                    device.write(b"HW_SAFE_!\n")
                    safe = device.readline().decode(errors="replace").strip()
                parsed = parse_identity(identity)
                parse_hardware_reply(status, "STATUS")
                parse_hardware_reply(safe, "SAFE")
                if parsed.hw_protocol < 1:
                    raise ValueError("hw_proto is unavailable")
                return candidate
            except Exception as exc:
                last_error = exc
        time.sleep(0.5)
    raise RuntimeError(f"could not verify commissioning protocol after upload: {last_error}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("setup", "build", "upload"))
    parser.add_argument("--port")
    args = parser.parse_args(argv)
    if args.action == "setup":
        subprocess.run(_cli() + ["config", "init", "--overwrite"], check=False)
        subprocess.run(_cli() + ["config", "set", "board_manager.additional_urls", "https://raw.githubusercontent.com/sparkfun/Arduino_Boards/main/IDE_Board_Manager/package_sparkfun_index.json"], check=True)
        subprocess.run(_cli() + ["core", "update-index"], check=True)
        for core in CORES:
            subprocess.run(_cli() + ["core", "install", core], check=True)
        for library in ("FlashStorage_SAMD", "PID"):
            subprocess.run(_cli() + ["lib", "install", library], check=True)
        return 0
    source = _source()
    if not source.joinpath("MINEVOLVER.ino").is_file():
        print("Firmware source SAMD21/MINEVOLVER/MINEVOLVER.ino is not present in this checkout. Restore/initialize the evolver-arduino source (or set EVOLVER_FIRMWARE_DIR) before building.", file=sys.stderr)
        return 2
    libraries = source.parents[1] / "libraries"
    command = _cli() + ["compile", "--fqbn", FQBN, "--libraries", str(libraries)]
    if args.action == "upload":
        # Arduino CLI accepts --libraries only while compiling.  Compile and
        # upload in one invocation so the locally vendored libraries are used.
        command += ["--port", args.port or "/dev/ttyACM0", "--upload"]
    command += [str(source)]
    subprocess.run(command, check=True)
    if args.action == "upload":
        port = args.port or "/dev/ttyACM0"
        time.sleep(2)
        try:
            verified_port = _verify_commissioning_protocol(port)
            print(f"Commissioning protocol verified safely on {verified_port}")
        except Exception as exc:
            print(f"Upload completed but commissioning protocol verification failed: {exc}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__": raise SystemExit(main())
