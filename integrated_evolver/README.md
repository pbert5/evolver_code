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

Start the local control-plane API:

```bash
nix run .#run-control-plane
```

Start the raw broadcast ingester:

```bash
nix run .#run-broadcast-ingest
```

Start the local service supervisor:

```bash
nix run .#run-supervisor
```

From the workspace root, the same apps are delegated through the main flake:

```bash
nix run .#run-control-plane
nix run .#run-broadcast-ingest
nix run .#run-supervisor
```

By default:

- the control API listens on `127.0.0.1:18082`
- the supervisor API listens on `127.0.0.1:18083`
- both services use `EVOLVER_DATA_DIR`, then XDG/HOME fallbacks
- both services talk to the existing eVOLVER server at
  `http://127.0.0.1:8081`

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
