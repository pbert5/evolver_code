# Task Completion

No automated test suite or linter is configured. When a coding task is done:

1. **Manual smoke-test** (if evolver server changed):
   - `nix build` succeeds in `evolver/`
   - `nix flake show` shows expected outputs
   - Inspect `result/bin/evolver-server` to verify patch/env wiring

2. **Manual smoke-test** (if DPU changed):
   - `nix flake show` succeeds in `dpu/`
   - `nix develop` enters shell without errors (full build may be slow due to old packages)

3. **Commit** each repo that changed (separately):
   ```bash
   git add <changed files> && git commit -m "..."
   ```
   Include `flake.lock` if inputs were updated.

No type checker, formatter, or test runner is enforced. Add them if introducing new code.
