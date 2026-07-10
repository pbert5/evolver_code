# Interacting with a Running eVOLVER Server

The server listens on TCP port `8081` and exposes a socket.io namespace:

- URL: `http://<evolver-host>:8081`
- Namespace: `/dpu-evolver`
- Default local dev URL: `http://127.0.0.1:8081`

When run on a workstation with `nix run`, the package uses mock serial automatically if the configured serial device is unavailable. On the Raspberry Pi NixOS service, mock serial is disabled and the configured hardware device must exist.

## Starting the server

```bash
cd evolver
nix run
```

Use a real serial device from a workstation:

```bash
EVOLVER_SERIAL_PORT=/dev/ttyUSB0 nix run
```

Force real hardware and fail if it is missing:

```bash
EVOLVER_MOCK_SERIAL=false nix run
```

Use a separate state directory for experiments:

```bash
EVOLVER_DATA_DIR=./state nix run
```

## Minimal Python client

Run this from the DPU dev shell, because it uses the legacy `socketIO-client` package pinned there.

```bash
cd dpu
nix develop
python
```

```python
from socketIO_client import SocketIO, BaseNamespace


class EvolverNamespace(BaseNamespace):
    def on_connect(self, *args):
        print("connected")

    def on_broadcast(self, data):
        print("broadcast:", data)

    def on_config(self, data):
        print("config:", data)

    def on_commandbroadcast(self, data):
        print("command accepted:", data)


socketIO = SocketIO("127.0.0.1", 8081)
evolver = socketIO.define(EvolverNamespace, "/dpu-evolver")

evolver.emit("getconfig", {}, namespace="/dpu-evolver")
evolver.emit(
    "command",
    {
        "param": "stir",
        "value": ["8"] * 16,
        "immediate": True,
        "recurring": True,
    },
    namespace="/dpu-evolver",
)

socketIO.wait(seconds=5)
socketIO.disconnect()
```

## Common events

Client-to-server events:

| Event | Payload | Server response |
|---|---|---|
| `getconfig` | `{}` | `config` with the full runtime config |
| `command` | Command object, see below | `commandbroadcast`; later `broadcast` includes data/config |
| `getdevicename` | `{}` | `broadcastname` |
| `setdevicename` | Any JSON object | `broadcastname` with the saved object |
| `getcalibrationnames` | `{}` | `calibrationnames` |
| `getfitnames` | `{}` | `fitnames` |
| `getcalibration` | `{"name": "..."}` | `calibration` |
| `setrawcalibration` | Calibration object | `calibrationrawcallback` with `success` |
| `setfitcalibration` | `{"name": "...", "fit": {...}}` | no explicit success event |
| `setactivecal` | `{"calibration_names": ["fit-name"]}` | `activecalibrations` |
| `getactivecal` | `{}` | `activecalibrations` |

Server-to-client events:

| Event | Meaning |
|---|---|
| `broadcast` | Periodic data and config snapshot from recurring serial commands |
| `commandbroadcast` | Echo of a received command event |
| `config` | Full server configuration |
| `broadcastname` | Device identity JSON |
| `calibrationnames` | Calibration name/type list |
| `fitnames` | Fit name/type list |
| `calibration` | Full calibration object |
| `activecalibrations` | Calibrations with active fits |

## Command payloads

Commands are JSON objects sent with the `command` event.

```json
{
  "param": "stir",
  "value": ["8", "8", "8", "8", "8", "8", "8", "8", "8", "8", "8", "8", "8", "8", "8", "8"],
  "immediate": true,
  "recurring": true
}
```

Important fields:

- `param`: one of the configured experimental params in `conf.yml`, such as `stir`, `temp`, `pump`, `od_90`, `od_135`, `od_led`, or `lxml`.
- `value`: a scalar or list matching that param's configured `fields_expected_outgoing`.
- `immediate`: when true, the command is inserted at the front of the serial queue.
- `recurring`: when true, the config is updated so the command is sent every broadcast cycle.

Examples:

```python
# Turn stirring on for all 16 vials.
evolver.emit("command", {
    "param": "stir",
    "value": ["8"] * 16,
    "immediate": True,
    "recurring": True,
}, namespace="/dpu-evolver")

# Set temperature raw values for all 16 vials.
evolver.emit("command", {
    "param": "temp",
    "value": ["4095"] * 16,
    "immediate": True,
    "recurring": True,
}, namespace="/dpu-evolver")

# Stop all pumps.
evolver.emit("command", {
    "param": "pump",
    "value": ["0"] * 48,
    "immediate": True,
    "recurring": False,
}, namespace="/dpu-evolver")
```

## Broadcast shape

The `broadcast` event contains:

```json
{
  "data": {
    "od_90": ["..."],
    "od_135": ["..."],
    "od_led": ["..."],
    "temp": ["..."],
    "stir": ["..."]
  },
  "config": {
    "stir": {
      "recurring": true,
      "fields_expected_outgoing": 17,
      "fields_expected_incoming": 17,
      "value": ["8", "..."]
    }
  },
  "ip": "192.168.1.8",
  "timestamp": 1783441780.7820349
}
```

With mock serial, the data arrays are zero-filled. With real hardware, they are the Arduino responses after the server sends the recurring command set.

## Existing clients

- `dpu/experiment/server_test.py` is the smallest working example.
- `dpu/experiment/template/eVOLVER.py` contains the higher-level experiment helper methods for stir, temperature, pump, chemostat, and calibration-aware workflows.
- `dpu/calibration/calibrate.py` shows the calibration events in use.
