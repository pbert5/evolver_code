# Firmware tooling

Use the workspace-local Arduino core state so setup/build invocations agree:
`nix run .#setup-arduino`, `nix run .#build-firmware`, and
`nix run .#upload-firmware -- --port /dev/ttyACM0`. The required FQBN is
`SparkFun:samd:samd21_mini`; both `arduino:samd` and `sparkfun:samd` are
installed. Upload verification must include USB re-enumeration and the protocol
handshake.

This integrated checkout currently does not include `SAMD21/MINEVOLVER`; build
and upload fail clearly until that source is restored (or `EVOLVER_FIRMWARE_DIR`
is provided). Do not substitute a different board definition.
