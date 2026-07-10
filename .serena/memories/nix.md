# Nix Packaging

## evolver (`evolver/flake.nix`)
- Single nixpkgs input (nixos-26.05), no poetry2nix needed
- `python3.withPackages`: aiohttp, pyserial, python-socketio, pyyaml, requests, six, websocket-client
- `evolver-package.nix`: `stdenvNoCC.mkDerivation` (`evolver-src`) + `writeShellApplication` (`evolver-server`)
- **Three `substituteInPlace` patches** in `postPatch`:
  1. `evolver_server.py`: `LOCATION = ...realpath(join(getcwd(), dirname(__file__)))` → uses `EVOLVER_DATA_DIR` env var
  2. `evolver_server.py`: conf.yml write path → `os.path.join(LOCATION, evolver.CONF_FILENAME)`
  3. `evolver.py`: conf.yml read path → `os.path.join(EVOLVER_DATA_DIR, CONF_FILENAME)`
- Launcher sets `PYTHONPATH` to include `evolver-src/share/evolver` so siblings are importable
- Initialises state dir on first run; never overwrites existing files

## DPU (`dpu/flake.nix`)
- Inputs: nixpkgs + poetry2nix
- `mkPoetryEnv { projectDir = ./.; python = pkgs.python39; preferWheels = true; }`
- poetry2nix overrides adding `setuptools` to buildInputs: `bokeh`, `django`, `django-crispy-forms`, `socketio-client`, `jinja2`
- If a new old package fails to build: add `prev.<pkg>.overridePythonAttrs (old: { buildInputs = (old.buildInputs or []) ++ [ prev.setuptools ]; })`

## NixOS module (`evolver/nix/evolver-module.nix`)
- Options: `services.evolver.{enable, package, serialPort, stateDir, user, group, openFirewall}`
- `serialPort` → systemd device unit via `lib.replaceStrings ["/"] ["-"] (lib.removePrefix "/" port)` + `.device`
- `ProtectSystem = "strict"` + `ReadWritePaths = [stateDir]` + `DeviceAllow = ["char-tty rw" serialPort]`
