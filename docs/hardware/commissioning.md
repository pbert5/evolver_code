# Commissioning

Commissioning is a recorded, operator-guided bring-up workflow. It is not a
calibration and it is not the `hardware-test` command. Before a real experiment,
commission the controller, verify physical mappings, calibrate temperature/OD
and configure fluidics separately.

Run `nix run .#commission-evolver -- --operator NAME`. It asks before output
actuation and writes a non-overwriting JSON record (default
`commissioning/report.json`). Use `--skip-flash` only after the separate
firmware upload has completed; `--resume PATH` retains a prior record as an
audit reference. PASS means the stated test passed, WARN needs review,
NOT_TESTABLE requires physical/operator evidence, and NOT_CALIBRATED is never a
claim that calibration occurred.
