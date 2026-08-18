# Firmware tooling

The custom source is the pinned `evolver-arduino` submodule at
`evolver-arduino/SAMD21/MINEVOLVER`. From the workspace root run:

```bash
nix run .#setup-arduino
nix run .#build-firmware
nix run .#upload-firmware -- --port /dev/ttyACM0
```

The target is `SparkFun:samd:samd21_mini`; setup installs both `arduino:samd`
and `sparkfun:samd`. Upload waits for USB re-enumeration, verifies
`WHO_ARE_YOU_!`, then requires `HW_STATUS_!` with `hw_proto=1`.
