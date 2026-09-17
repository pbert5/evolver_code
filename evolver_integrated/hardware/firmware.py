"""Pinned, artifact-bound Arduino CLI workflow for min-eVOLVER firmware."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from glob import glob
from pathlib import Path

FQBN = "SparkFun:samd:samd21_mini"
CORES = ("arduino:samd", "sparkfun:samd")
SOURCE_REPOSITORY = "https://github.com/pbert5/evolver-arduino.git"
SOURCE_COMMIT = "952a6fd713c40caa072444a0e0e3fc4fc6ee4639"
DEFAULT_ARTIFACT = Path(".artifacts/MINEVOLVER.ino.bin")
PROVENANCE_SUFFIX = ".provenance.json"


def _source() -> Path:
    return Path(os.environ.get("EVOLVER_FIRMWARE_DIR", "evolver-arduino/SAMD21/MINEVOLVER"))


def _cli() -> list[str]:
    data = Path(os.environ.get("EVOLVER_ARDUINO_DATA", ".arduino-cli"))
    data.mkdir(parents=True, exist_ok=True)
    return ["arduino-cli", "--config-file", str(data / "arduino-cli.yaml")]


def _artifact_path(value: str | None) -> Path:
    return Path(value or os.environ.get("EVOLVER_FIRMWARE_ARTIFACT", str(DEFAULT_ARTIFACT)))


def _provenance_path(artifact: Path) -> Path:
    return artifact.with_name(artifact.name + PROVENANCE_SUFFIX)


def _source_identity(source: Path) -> tuple[str, str]:
    commit = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    repo = subprocess.run(
        ["git", "-C", str(source), "remote", "get-url", "origin"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return repo.rstrip("/"), commit


def _canonical_repo(repo: str) -> str:
    return repo.rstrip("/").removesuffix(".git")


def _source_worktree_status(source: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(source), "status", "--porcelain=v1", "--untracked-files=all"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _validate_source(source: Path) -> tuple[str, str]:
    if not (source / "MINEVOLVER.ino").is_file():
        raise ValueError("Firmware source SAMD21/MINEVOLVER/MINEVOLVER.ino is not present")
    status = _source_worktree_status(source)
    if status:
        raise ValueError(f"firmware source worktree is dirty: {status.splitlines()[0]}")
    repo, commit = _source_identity(source)
    if _canonical_repo(repo) != _canonical_repo(SOURCE_REPOSITORY):
        raise ValueError(f"firmware source repository drift: {repo}")
    if commit != SOURCE_COMMIT:
        raise ValueError(f"firmware source commit drift: expected {SOURCE_COMMIT}, found {commit}")
    return repo, commit


def _digest(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _load_and_verify_artifact(artifact: Path, source: Path) -> dict:
    provenance = _provenance_path(artifact)
    if not artifact.is_file() or not provenance.is_file():
        raise ValueError(f"missing immutable firmware artifact or provenance: {artifact}")
    try:
        metadata = json.loads(provenance.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid firmware provenance: {provenance}") from exc
    if not isinstance(metadata, dict):
        raise ValueError(f"invalid firmware provenance: {provenance}")
    if metadata.get("schema") != "evolver-firmware-provenance/v1":
        raise ValueError("unsupported firmware provenance schema")
    repo, commit = _validate_source(source)
    recorded_repo = metadata.get("source_repository", "")
    if _canonical_repo(recorded_repo) != _canonical_repo(SOURCE_REPOSITORY):
        raise ValueError("firmware provenance repository mismatch")
    if metadata.get("source_commit") != SOURCE_COMMIT or commit != metadata.get("source_commit"):
        raise ValueError("firmware provenance source commit mismatch")
    if _canonical_repo(recorded_repo) != _canonical_repo(repo):
        raise ValueError("firmware source repository drift")
    if metadata.get("fqbn") != FQBN:
        raise ValueError("firmware provenance FQBN mismatch")
    if metadata.get("source_path") != "SAMD21/MINEVOLVER/MINEVOLVER.ino":
        raise ValueError("firmware provenance source path mismatch")
    recorded = metadata.get("artifact", {})
    if not isinstance(recorded, dict):
        raise ValueError("firmware provenance artifact metadata is invalid")
    digest, size = _digest(artifact)
    if recorded.get("sha256") != digest or recorded.get("size") != size:
        raise ValueError("firmware artifact SHA-256 or size mismatch")
    if recorded.get("filename") != artifact.name:
        raise ValueError("firmware provenance artifact filename mismatch")
    return metadata


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


def _build(source: Path, artifact: Path) -> int:
    repository, commit = _validate_source(source)
    provenance = _provenance_path(artifact)
    if artifact.exists() or provenance.exists():
        raise ValueError(f"refusing to overwrite immutable firmware artifact: {artifact}")
    artifact.parent.mkdir(parents=True, exist_ok=True)
    libraries = source.parents[1] / "libraries"
    with tempfile.TemporaryDirectory(prefix="evolver-firmware-") as build_dir:
        subprocess.run(
            _cli()
            + [
                "compile",
                "--fqbn",
                FQBN,
                "--libraries",
                str(libraries),
                "--output-dir",
                build_dir,
                str(source),
            ],
            check=True,
        )
        candidates = sorted(Path(build_dir).glob("*.bin"))
        if len(candidates) != 1:
            raise ValueError(f"expected one compiled firmware .bin, found {len(candidates)}")
        shutil.copyfile(candidates[0], artifact)
    digest, size = _digest(artifact)
    metadata = {
        "schema": "evolver-firmware-provenance/v1",
        "source_repository": repository,
        "source_commit": commit,
        "source_path": "SAMD21/MINEVOLVER/MINEVOLVER.ino",
        "fqbn": FQBN,
        "build_toolchain": {
            "arduino_cli": subprocess.run(
                _cli() + ["version"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        },
        "artifact": {"filename": artifact.name, "sha256": digest, "size": size},
    }
    provenance.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    print(f"Built immutable firmware artifact: {artifact} ({size} bytes, sha256={digest})")
    return 0


def _upload(source: Path, artifact: Path, port: str) -> int:
    _load_and_verify_artifact(artifact, source)
    subprocess.run(
        _cli() + ["upload", "--fqbn", FQBN, "--port", port, "--input-dir", str(artifact.parent)],
        check=True,
    )
    time.sleep(2)
    try:
        verified_port = _verify_commissioning_protocol(port)
        print(f"Commissioning protocol verified safely on {verified_port}")
    except Exception as exc:
        print(f"Upload completed but commissioning protocol verification failed: {exc}", file=sys.stderr)
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("setup", "build", "upload"))
    parser.add_argument("--port")
    parser.add_argument("--artifact")
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
    try:
        source = _source()
        artifact = _artifact_path(args.artifact)
        if args.action == "build":
            return _build(source, artifact)
        return _upload(source, artifact, args.port or "/dev/ttyACM0")
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"Firmware {args.action} refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
