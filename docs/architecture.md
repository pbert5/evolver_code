# eVOLVER Architecture

## Overview

Two components communicate over a local network via socket.io:

```
┌─────────────────────────────────┐      socket.io       ┌──────────────────────┐
│   Raspberry Pi (evolver server) │ ◄──────────────────► │  Workstation (DPU)   │
│                                 │   port 8081           │                      │
│  evolver.py (entry)             │   /dpu-evolver ns     │  calibrate.py        │
│  evolver_server.py (socket.io)  │                       │  experiment scripts  │
│  multi_server.py (aiohttp)      │                       │  graphing Django app │
│  serial_discovery.py            │                       └──────────────────────┘
│  provisioning.py                │
│            │                    │
│            │ serial /dev/ttyUSB0│
│            │  or /dev/ttyAMA0   │
│            ▼                    │
│  Arduino (SAMD21 or Nano)       │
│  (temp, OD, stir, pump)         │
│  MINEVOLVER firmware            │
└─────────────────────────────────┘
```

## evolver server (Raspberry Pi)

Entry point: `evolver/evolver/evolver.py`

1. Reads `conf.yml` from the state directory (`EVOLVER_DATA_DIR`, default `/var/lib/evolver`).
2. Starts an aiohttp web application via `MultiServer` on port 8081.
3. Attaches a socket.io `AsyncServer` to the app (`evolver_server.py`).
4. Runs a broadcast loop: every `broadcast_timing` seconds (default 20 s), all recurring commands are sent to the Arduino over serial and the response data is pushed to connected DPU clients as a `broadcast` event.

### Serial protocol

Commands are sent as `param,value1,value2,...,_!` and responses are read as `param,response_char,data1,data2,...,end`. After each read, an ACK is sent. `RECURRING` commands run every broadcast cycle; `IMMEDIATE` commands are inserted at the front of the queue on demand.

### Device discovery and provisioning

Before the server can use a device it must be identified and provisioned. `serial_discovery.py` scans serial ports, sends `WHO_ARE_YOU_!` to each, and classifies the response. `provisioning.py` manages the provisioning state machine and the `PROVISION` / `CLEAR_ID` handshake. See `docs/hardware.md` for the full workflow.

### State files (all mutable, never in Nix store)

| File | Content |
|---|---|
| `conf.yml` | Full `evolver_conf` dict; rewritten on every `command` socket event |
| `calibrations.json` | List of named calibration objects with raw data and polynomial fits |
| `evolver-config.json` | Device identity / name |

## DPU (workstation)

The DPU is a collection of Python scripts run by researchers, not a long-running service.

- **`calibration/calibrate.py`** — connects to the evolver server, fetches raw calibration data, fits curves with scipy, and uploads the fit back to the server.
- **`experiment/server_test.py`** — template experiment script that sends commands on a timer.
- **`graphing/`** — Django 1.8.6 web app for visualising experiment time-series data with bokeh.

The DPU communicates with the evolver server using the legacy `socketIO-client 0.7.2` package (class-based API), which is a different library from the `python-socketio` used by the server.

## Service management (NixOS)

On NixOS, the evolver server is managed by a systemd service (see `evolver/nix/evolver-module.nix`). This replaces the original supervisord + cron watchdog setup. Systemd restarts the process automatically on failure with a 10 s cooldown, and logs go to journald.
