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

Keep actuator power disconnected while flashing. The current firmware boots
safe: pumps, stirrers, heaters, and OD LEDs are off and temperature PID is
disabled. A successful post-flash status includes
`temp_control=off,mode=idle`; the upload helper also sends `HW_SAFE_!`.

For a controller that was previously warm at idle, verify this state explicitly
before reconnecting actuator power:

```bash
nix run .#hardware-test -- protocol --port /dev/ttyACM0 --debug
```

Do not issue a normal `temp` command during this check. If an MP915 resistor
becomes warm while idle after actuator power is connected, disconnect actuator
power immediately and investigate the heater driver/wiring.
