# Integrated eVOLVER Runtime

This repository contains the proposed integrated local runtime for eVOLVER.

The legacy workspace projects have been moved under `deprecated/`:

- `deprecated/evolver` is the legacy hardware-facing Socket.IO and serial server.
- `deprecated/dpu` is the existing experiment-script and graphing workflow.
- `deprecated/evolver-arduino` is the firmware workspace.
- `deprecated/evolver_plan` is the previous planning workspace.

The root project now contains the new control plane, data service, runner
management, maintenance-job coordination, TUI, and local API experiments.

## What Runs

### Holistic Dev

Use the supervisor as the normal integrated development entrypoint:

```bash
nix run .#run-supervisor
```

The supervisor loads `evolver_integrated/service_catalog.yaml`, starts
autostart services such as the control plane, and owns service lifecycle actions
for the TUI. This is the path to use when you want the local runtime to behave
like the future system service topology while still running from the current
source tree.

In another terminal, launch the TUI:

```bash
nix run .#run-tui
```

For TUI-only interaction testing, launch demo mode:

```bash
nix run .#run-tui -- --demo
```

Demo mode loads `evolver_integrated/tui/demo_data.json` with sample evolver
units, devices, materials, protocols, and experiments so the TUI can be tested
without attached hardware or populated local inventory. Inside the TUI, press
`d` to load the same demo data into a running session.

By default:

- the supervisor API listens on `127.0.0.1:18083`
- the control API listens on `127.0.0.1:18082`
- services use `EVOLVER_DATA_DIR`, then XDG/HOME fallbacks
- hardware-facing communication still targets the existing eVOLVER server at
  `http://127.0.0.1:8081`

### Piecewise Dev

Run individual services directly when debugging one component or when you do
not want the supervisor to own subprocess lifecycle.

Start only the local control-plane API:

```bash
nix run .#run-control-plane
```

Start only the raw broadcast ingester:

```bash
nix run .#run-broadcast-ingest
```

Start only the TUI:

```bash
nix run .#run-tui
```

When running the control plane by hand but still using a separately running
supervisor, point it at the supervisor API:

```bash
nix run .#run-control-plane -- --supervisor-url http://127.0.0.1:18083
```

## Development

Run tests from the repository root:

```bash
nix develop
pytest tests/ -q
```

Run the folder-level flake check:

```bash
nix flake check
```

## Boundaries

This package should not open serial ports directly. The legacy hardware server
continues to own serial communication until a future hardware-service rewrite.

Experiment user code should run through runner isolation. The control-plane
process coordinates lifecycle and policy; it should not import user experiment
scripts into its own process.

Raw measurements should be persisted before experiment-specific processing
whenever practical.

See [docs/architecture.md](docs/architecture.md) for the current phased design.
