# Agent Working Agreement — evolver_code

## Required First Steps

1. Call `mcp__serena__initial_instructions` and follow the Serena manual.
2. Activate the project with `mcp__serena__activate_project` at `/home/ash/Documents/work/evolver_code`.
3. Read project memories when the memory tool is available, starting with `core`, then follow references as needed.

## Shell Usage

Always prefix shell commands with `rtk` so command output stays token-efficient:
- `rtk git status --short`
- `rtk nix flake check`
- `rtk pytest -q`

## Serena Tool Usage

Use Serena for semantic navigation and edits across both repos (`evolver/` and `dpu/`):
- Symbol overview before reading full files.
- `find_symbol`, `find_referencing_symbols` for understanding call graphs.
- `replace_symbol_body`, `insert_after_symbol` for structure-aware edits.
- `search_for_pattern` when a symbol name is unknown.

## Project Layout

Two independent git repos under this directory:
- `evolver/` — Raspberry Pi hardware server (Python + Nix flake)
- `dpu/` — workstation experiment/calibration client (Python 3.9 + Nix flake)
- `docs/` — project documentation

Each repo has its own `flake.nix` and must be committed separately.

Run Nix checks from each repo:
- `cd evolver && rtk nix flake check`
- `cd dpu && rtk nix flake check`

## Commits

Commit completed changes . The two repos (`evolver/` and `dpu/`) are committed independently, and the workspace root is not itself a git repo.

## Docs

Keep `docs/` in sync with significant changes:
- `docs/architecture.md` — system overview
- `docs/nix.md` — Nix dev shells and NixOS service
- `docs/calibration.md` — calibration workflow
