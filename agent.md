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

Use the root flake dev environment for project commands that need repository
dependencies, especially TUI tests and tooling that require `textual`:
- `rtk nix develop --command pytest -q tests/test_tui.py`
- `rtk nix develop --command flake8 evolver_integrated tests`

## Languages
- python
    - use Serena for all Python interaction. This is explicit and mandatory: navigate Python with Serena, inspect Python symbols with Serena, and make Python symbol edits with Serena whenever a symbol-aware edit applies. 

## Serena Tool Usage

Use Serena for all Python interaction. This is explicit and mandatory: navigate Python with Serena, inspect Python symbols with Serena, and make Python symbol edits with Serena whenever a symbol-aware edit applies.

- Symbol overview before reading full files.
- `find_symbol`, `find_referencing_symbols` for understanding call graphs.
- `replace_symbol_body`, `insert_after_symbol` for structure-aware edits.
- `search_for_pattern` when a symbol name is unknown.
- Use shell tools for tests, formatting, docs, generated output, and non-Python files.

## Project Layout

- `data/` contains JSON objects and LinkML schemas that drive runtime behavior.
- `docs/` contains architecture notes, plans, and design braindumps.
- `evolver_integrated/` contains the control plane, supervisor, data service, runner management, and TUI source.
- `evolver_integrated/tui` contians the tui source
- `tests/` contains the integrated runtime test suite.
- `deprecated/` contains the previous workspace-level projects and hardware/examples material.

## Commits

Commit after each completed step so work is preserved as small, reviewable checkpoints. Do not wait until the end of a long task to commit unrelated stages together.

Use the root repository at `/home/ash/Documents/work/evolver_code` for integrated runtime changes.
Keep commit messages scoped to the step that was just completed.

## Docs

Keep `docs/` in sync with significant changes:
- `docs/architecture.md` — system overview
- `docs/nix.md` — Nix dev shells and NixOS service
- `docs/calibration.md` — calibration workflow
