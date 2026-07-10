# Running eVOLVER Components

Quick-start guide for running the evolver server and DPU scripts. For Nix setup details see [nix.md](nix.md); for calibration see [calibration.md](calibration.md); for socket.io usage after the server is up see [interacting.md](interacting.md).

## Python version note

Both repos target **Python 3.6** (the `evolver.py` shebang is `python3.6`; the DPU deps are pinned to that era). `pkgs.python36` was removed from nixpkgs around 23.05 and `pkgs.python39` around 25.05. The flakes fall back to python39 → python311 when the exact interpreter is absent. To get the true 3.6 environment, pin the nixpkgs input to `nixos-22.11` or earlier in each flake.

---

## Flake commands (both repos)

```bash
# Enter the reproducible dev shell (most common)
nix develop

# Run all checks (flake8 lint) — same checks CI would run
nix flake check

# Build the installable package (evolver only)
cd evolver && nix build            # → ./result/bin/evolver-server

# Run the server directly from the flake without a separate build step
cd evolver && nix run              # equivalent to ./result/bin/evolver-server
```

---

## evolver server (Raspberry Pi)

### Development run

```bash
cd evolver
nix develop
cd evolver
python evolver.py
```

The server reads `conf.yml` from the same directory, listens on port 8081, and begins broadcasting to connected DPU clients every `broadcast_timing` seconds (default 20 s).

### Production run (built binary)

```bash
cd evolver
nix build            # produces ./result/bin/evolver-server
./result/bin/evolver-server
```

On first run the binary copies default config files (`conf.yml`, `calibrations.json`, `evolver-config.json`) into the state directory and then starts the server. Existing files are never overwritten.

Use a custom state directory:

```bash
EVOLVER_DATA_DIR=./my-evolver-data ./result/bin/evolver-server
```

### NixOS systemd service

On NixOS the server is managed automatically. Useful commands:

```bash
# Start / stop / restart
sudo systemctl start evolver
sudo systemctl stop evolver
sudo systemctl restart evolver

# Watch live logs
journalctl -u evolver -f

# Check status
systemctl status evolver
```

See [nix.md](nix.md) for the NixOS module configuration.

### Tests (evolver)

The test suite is flake8 lint. Run inside the dev shell or via the flake:

```bash
# Inside nix develop
flake8 --ignore=E501 --exclude=evolver/socketIO_client evolver/

# Or via the flake (no shell entry needed)
nix flake check
```

`socketIO_client/` is vendored legacy code — excluded from lint.

---

## DPU (workstation)

All DPU scripts are run from inside the Nix dev shell:

```bash
cd dpu
nix develop
```

The shell prints a reminder of the available commands on entry.

### Calibration

```bash
python calibration/calibrate.py --help
```

See [calibration.md](calibration.md) for the full workflow.

### Experiment script

Edit `experiment/server_test.py` to set `EVOLVER_IP` and `EVOLVER_PORT`, then run:

```bash
python experiment/server_test.py
```

The script connects to the evolver server, listens for `broadcast` events, and sends `command` events on a timer. Use it as a template for custom experiment scripts.

### Graphing web app

```bash
cd graphing/src
python manage.py runserver
```

Open `http://127.0.0.1:8000` in a browser. Experiment data directories must include `expt` in their name to be picked up by the graphing tool.

### Tests (DPU)

```bash
# Inside nix develop
flake8 --ignore=E501 calibration/ experiment/ graphing/

# Or via the flake
nix flake check
```
