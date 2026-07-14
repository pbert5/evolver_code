# Integrated eVOLVER Runtime

This folder contains the proposed integrated local runtime for eVOLVER.

It intentionally lives beside the existing projects instead of inside any one
of them:

- `../evolver` remains the legacy hardware-facing Socket.IO and serial server.
- `../dpu` remains the existing experiment-script and graphing workflow.
- `../integrated_evolver` contains the new control plane, data service,
  runner management, maintenance-job coordination, and local API experiments.

The goal is to let the new architecture evolve without making the current
hardware server package responsible for every future system concern.

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

From the workspace root, the same apps are delegated through the main flake:

```bash
nix run .#run-supervisor
nix run .#run-control-plane
nix run .#run-broadcast-ingest
nix run .#run-tui
```

## Development

Run tests from this folder:

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
