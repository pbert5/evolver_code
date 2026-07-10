# Conventions

## Python style
- No type hints (legacy codebase, pre-3.9 style)
- socket.io handlers are `async def on_<event>(sid, data)` decorated with `@sio.on`
- Global mutable state via module-level vars (`evolver_conf`, `serial_connection`, `command_queue`) — do not refactor without understanding the threading model
- `flush=True` on all `print()` calls in evolver server (required for supervisord/journald log capture)

## Nix conventions (evolver/)
- Never use `default.nix`; explicit filenames under `nix/`
- Patches applied via `substituteInPlace` in `postPatch` — keep them minimal and to exact string matches
- `EVOLVER_DATA_DIR` env var is the single hook for redirecting all mutable file I/O; do not add more env vars without updating the module

## Commits
- Commit after each completed feature or fix before moving to the next task
- Commit evolver/ and dpu/ repos separately (they are independent git repos)
