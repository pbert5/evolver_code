# Tech Stack

## evolver (server)
- Python 3 (nixpkgs default, currently 3.13 in nixos-26.05)
- aiohttp — HTTP/WebSocket server
- python-socketio (server side, `AsyncServer`) — socket.io namespace `/dpu-evolver`
- pyserial — serial comm with Arduino (`/dev/ttyAMA0`, 9600 baud)
- pyyaml — conf.yml load/dump
- Nix flake (`evolver/flake.nix`); no pyproject.toml / requirements pinning beyond nixpkgs

## dpu (client)
- Python **3.9.x** exactly (`>3.9, <3.10` constraint in pyproject.toml)
- socketIO-client **0.7.2** — legacy class-based API (`SocketIO`, `BaseNamespace`), imported as `socketIO_client`
- Django **1.8.6** — graphing web app
- bokeh **0.10.0** — plotting in Django app
- scipy, numpy, matplotlib — curve fitting and calibration plots
- Poetry + `poetry.lock` for dep management; Nix via poetry2nix (`dpu/flake.nix`)

## Nix
- nixpkgs channel: `nixos-26.05`
- poetry2nix for DPU; direct `python3.withPackages` for evolver
- `preferWheels = true` in DPU shell (old packages need it)
- Old pre-PEP-517 packages (django, bokeh, socketio-client, jinja2, django-crispy-forms) get `setuptools` added via poetry2nix overrides
