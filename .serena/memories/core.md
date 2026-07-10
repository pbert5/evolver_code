# evolver_code — Project Core

Two independent git repos under `/home/ash/Documents/work/evolver_code/`:
- `evolver/` — Raspberry Pi hardware server daemon
- `dpu/` — workstation experiment/calibration client

Each repo has its own `flake.nix` at its root. There is no top-level git repo; the `evolver_code/` directory is just a workspace container.

## Source map

| Path | Purpose |
|---|---|
| `evolver/evolver/evolver.py` | Server entry point (run as `__main__`) |
| `evolver/evolver/evolver_server.py` | socket.io event handlers + serial comms |
| `evolver/evolver/multi_server.py` | `MultiServer` — aiohttp app runner |
| `evolver/evolver/conf.yml` | Default runtime config (mutable at runtime) |
| `evolver/evolver/calibrations.json` | Calibration data (mutable at runtime) |
| `evolver/nix/evolver-package.nix` | Nix package (patches + launcher) |
| `evolver/nix/evolver-module.nix` | NixOS systemd service module |
| `dpu/calibration/calibrate.py` | Calibration CLI (connects to evolver, fits curves) |
| `dpu/experiment/server_test.py` | Example experiment script |
| `dpu/graphing/src/` | Django 1.8.6 graphing web app |
| `dpu/pyproject.toml` | Poetry deps (Python 3.9, old packages) |

## Key invariants
- `evolver_server.py` `LOCATION` and all mutable-file paths honour `EVOLVER_DATA_DIR`; default is `__file__` dir (Nix patch applied at build time).
- `conf.yml` is written back by the server on every `command` socket event — it must be mutable.
- DPU uses `socketIO_client` (import name) = the legacy `socketIO-client 0.7.2` PyPI package, **not** `python-socketio`.

Module-specific details: `mem:evolver/core`, `mem:dpu/core`
Nix packaging details: `mem:nix`
