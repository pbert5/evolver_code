# Claude Working Agreement — evolver_code

## Required First Steps

1. Call `mcp__plugin_claude-code-home-manager_serena__initial_instructions` and follow the Serena manual.
2. Activate the project: `mcp__plugin_claude-code-home-manager_serena__activate_project` with path `/home/ash/Documents/work/evolver_code`.
3. Read `mem:core` as the entry point to project memories, then follow references as needed.

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

## Commits

Commit completed changes after each feature or fix before moving on to the next task. The two repos (`evolver/` and `dpu/`) are committed independently.

## Docs

Keep `docs/` in sync with significant changes:
- `docs/architecture.md` — system overview
- `docs/nix.md` — Nix dev shells and NixOS service
- `docs/calibration.md` — calibration workflow
