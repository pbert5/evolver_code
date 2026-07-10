# DPU — Client Core

## Components
- `calibration/calibrate.py` — CLI tool: connects to evolver, fetches raw calibration data, fits curves (sigmoid/linear/constant/3d), optionally uploads fit back
- `experiment/server_test.py` — example script: sends stir/temp commands in a loop
- `graphing/src/` — Django 1.8.6 web app (`cloudevolution` project) for visualising experiment data with bokeh 0.10.0

## Calibration workflow (`calibrate.py`)
1. Connect via `socketIO_client.SocketIO(ip, port)` → `EvolverNamespace` on `/dpu-evolver`
2. Emit `getcalibration {name}` → receive raw data
3. Fit with scipy: `sigmoid_fit`, `linear_fit`, `constant_fit`, or `three_dimension_fit`
4. Emit `setfitcalibration {name, fit}` to upload result

## Fit types
| Type | Use case | Params |
|---|---|---|
| sigmoid | OD calibration | single param (e.g. `od_90`) |
| linear | temp calibration | single param |
| constant | simple scaling | single param |
| 3d | 2-param OD (od_90 + od_135) | two params |

## Important: legacy socket.io client
- Import: `from socketIO_client import SocketIO, BaseNamespace`
- PyPI package: `socketIO-client==0.7.2`
- API: class-based namespaces, `socketIO.define(EvolverNamespace, '/dpu-evolver')`
- **Not** the same as `python-socketio` (used by the server)

## Django app (graphing)
- Settings: `dpu/graphing/src/cloudevolution/settings.py`
- Run: `cd dpu/graphing/src && python manage.py runserver`
- Static assets committed to `static_in_env/static_root/` (includes bokeh 0.10.0 JS/CSS)
