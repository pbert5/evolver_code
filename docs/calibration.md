# Calibration Workflow

Calibration maps raw Arduino sensor values to physical units (OD, temperature). Raw data is collected by the evolver server and stored in `calibrations.json`; the DPU fits curves to produce calibration coefficients that are sent back to the server.

## 1. Collect raw data

Use the eVOLVER GUI or a custom script to run a calibration experiment and store the raw data on the evolver server (via the `setrawcalibration` socket.io event).

## 2. List available calibrations

```bash
# from inside `nix develop` in dpu/
python calibration/calibrate.py -a <evolver-ip> --get-calibration-names
```

## 3. Fit a calibration

```bash
python calibration/calibrate.py \
  -a <evolver-ip> \
  -n <calibration-name> \
  -t <fit-type> \
  -f <fit-name> \
  -p <param>[,<param2>]
```

### Fit types

| Type | `-t` flag | Params (`-p`) | Use case |
|---|---|---|---|
| Sigmoid | `sigmoid` | single, e.g. `od_90` | OD calibration (single angle) |
| Linear | `linear` | single, e.g. `temp` | Temperature calibration |
| Constant | `constant` | single | Simple multiplicative scaling |
| 3D polynomial | `3d` | two, e.g. `od_90,od_135` | OD calibration (dual angle) |

### Example — OD sigmoid fit

```bash
python calibration/calibrate.py \
  -a 192.168.1.8 \
  -n my_od_calibration \
  -t sigmoid \
  -f od_sigmoid_2024 \
  -p od_90
```

### Flags

| Flag | Effect |
|---|---|
| `-y` / `--always-yes` | Skip the "upload to evolver?" prompt |
| `-r` / `--no-graph` | Skip the matplotlib plot |

## 4. Activate a fit

After uploading, mark a fit as active via the `setactivecal` socket.io event (GUI or script).

## Calibration data format (`calibrations.json`)

```json
[
  {
    "name": "my_od_calibration",
    "calibrationType": "od",
    "params": ["od_90"],
    "raw": [
      {
        "param": "od_90",
        "vialData": [[[...replicates...], ...points...], ...16 vials...]
      }
    ],
    "measuredData": [...actual OD values...],
    "fits": [
      {
        "name": "od_sigmoid_2024",
        "type": "sigmoid",
        "coefficients": [[a, b, c, d], ...16 vials...],
        "timeFit": 1234567890.0,
        "active": true,
        "params": ["od_90"]
      }
    ]
  }
]
```
