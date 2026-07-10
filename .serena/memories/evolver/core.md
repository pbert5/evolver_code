# evolver — Server Core

## Runtime model
1. `evolver.py` (entry): reads `conf.yml`, gets local IP, starts `MultiServer` (aiohttp) on port 8081, enters broadcast loop
2. `evolver_server.py`: socket.io `AsyncServer` attached to the aiohttp app; handles all `/dpu-evolver` namespace events
3. `multi_server.py` `MultiServer`: wraps aiohttp `AppRunner`/`TCPSite` in a background thread; one `web.Application` per port

## Serial communication (`serial_communication`)
- Protocol: `param + comma-separated values + serial_end_outgoing ("_!")` → send; read response; send ACK
- Expects `echo_response_char` ('e') for commands, `data_response_char` ('b') for sensor reads
- `command_queue`: list of `{param, value, type}` dicts; `IMMEDIATE` commands skip to front; `RECURRING` commands are re-added each broadcast cycle
- `broadcast_timing` (default 20s) controls how often sensor data is pushed to DPU clients

## Mutable state files (all under `EVOLVER_DATA_DIR`)
- `conf.yml` — full `evolver_conf` dict; rewritten on every `command` event
- `calibrations.json` — list of calibration objects with fits
- `evolver-config.json` / `test_device.json` — device identity

## socket.io events (namespace `/dpu-evolver`)
| Event | Handler | Notes |
|---|---|---|
| `command` | `on_command` | updates conf, queues immediate cmd |
| `getconfig` | `on_getlastcommands` | emits full `evolver_conf` |
| `getcalibrationnames` | `on_getcalibrationnames` | |
| `getfitnames` | `on_getfitnames` | |
| `getcalibration` | `on_getcalibration` | by name |
| `setrawcalibration` | `on_setrawcalibration` | upsert by name |
| `setfitcalibration` | `on_setfitcalibrations` | appends fit to calibration |
| `setactivecal` | `on_setactiveodcal` | sets fit.active flags |
| `getactivecal` | `on_getactivecal` | |
| `getdevicename` | `on_getdevicename` | reads device JSON |
| `setdevicename` | `on_setdevicename` | writes device JSON |
| `broadcast` (emit) | — | sensor data pushed every cycle |

## NixOS service
- Module: `evolver/nix/evolver-module.nix`
- `services.evolver.{enable, package, serialPort, stateDir, user, group, openFirewall}`
- Default stateDir: `/var/lib/evolver`; user: `evolver`; group: `evolver` + `dialout`
- `Restart = on-failure` replaces supervisord + cron watchdog
