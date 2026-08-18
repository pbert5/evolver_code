# min-eVOLVER hardware

This section separates firmware tooling, dry-safe hardware testing, and guided
commissioning. The direct serial backend is for bring-up only; the API is shaped
so a future `evolver-hardwared` can exclusively own the port.

For a first assembled device, follow the complete [bench testing and
commissioning playbook](../testing/min-evolver-hardware-playbook.md). Concise
references are [commissioning.md](commissioning.md),
[hardware-testing.md](hardware-testing.md), [firmware.md](firmware.md),
[hardware-map.md](hardware-map.md), and [troubleshooting.md](troubleshooting.md).

For read-only live observation of both Sleeve thermistors and photodiodes, run
`nix run .#run-tui` and press `m`. The monitor keeps commissioning safe mode,
never actuates outputs, and is documented in the
[bench playbook](../testing/min-evolver-hardware-playbook.md#optional-live-sensor-monitor).
