# Nix — Environment Management and Launching

Both the evolver server and the DPU client have Nix flakes that replace manual `pip install` / `poetry install` and the old supervisord setup.

## evolver server (`evolver/`)

### Dev shell

```bash
cd evolver
nix develop
# Python 3 shell with: aiohttp, python-socketio, pyserial, pyyaml, requests, websocket-client, six
```

### Build the server binary

```bash
cd evolver
nix build            # produces ./result/bin/evolver-server
```

The binary initialises the state directory on first run (copies `conf.yml`, `calibrations.json`, etc. from the package defaults) and then starts the server. Existing files are never overwritten on upgrade.

### Run with a custom state directory

```bash
EVOLVER_DATA_DIR=./my-evolver-data result/bin/evolver-server
```

### NixOS service (Raspberry Pi deployment)

Add the evolver flake as an input to your NixOS configuration and enable the module:

```nix
# flake.nix inputs
evolver.url = "git+file:/path/to/evolver";  # or github URL

# host configuration
{ inputs, system, ... }: {
  imports = [ inputs.evolver.nixosModules.evolver ];

  services.evolver = {
    enable = true;
    package = inputs.evolver.packages.${system}.evolver;
    serialPort = "/dev/ttyAMA0";   # default
    openFirewall = true;           # opens TCP 8081
    # stateDir = "/var/lib/evolver";  # default
  };
}
```

The systemd service:
- Runs as a dedicated `evolver` user in the `dialout` group (serial port access).
- Restarts automatically on failure (`Restart = on-failure`, 10 s cooldown).
- Waits for the serial device unit before starting.
- Writes state under `stateDir` (`/var/lib/evolver` by default).

Logs: `journalctl -u evolver -f`

## DPU client (`dpu/`)

The DPU has very specific version requirements (Python 3.9, Django 1.8.6, bokeh 0.10.0, socketIO-client 0.7.2). The flake uses poetry2nix with the existing `poetry.lock` to reproduce these exactly.

### Dev shell

```bash
cd dpu
nix develop
# Python 3.9 shell with all deps from poetry.lock
```

The shell prints usage hints for the main scripts on entry.

### Updating dependencies

If you update `pyproject.toml` / `poetry.lock`:

1. Run `poetry update` (or `poetry lock`) in `dpu/`.
2. Run `nix develop` to verify the new lock file builds.
3. If a new old package fails with a build error, add a `setuptools` override in `dpu/flake.nix` under the `overrides` block.

### Troubleshooting poetry2nix builds

Old packages that predate PEP 517 often fail with "no setup.py / pyproject.toml" errors. Fix:

```nix
my-package = prev.my-package.overridePythonAttrs (old: {
  buildInputs = (old.buildInputs or [ ]) ++ [ prev.setuptools ];
});
```
