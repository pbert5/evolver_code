# Hardware-testing playbook

This is the concise command reference. For a first assembled device, follow the
[complete bench testing and commissioning playbook](../testing/min-evolver-hardware-playbook.md).

Remove liquid/vials before commissioning. The firmware protocol is explicit and
always replies with `HW|1|OK|OPERATION|key=value,...` or an `ERR` reply. It is
separate from normal `od_90`, `od_led`, `temp`, `stir`, and `pump` controls.

Run this first bench sequence:

```bash
nix run .#hardware-test -- usb --port /dev/ttyACM0 --debug
nix run .#hardware-test -- protocol --port /dev/ttyACM0 --debug
nix run .#hardware-test -- sensors --port /dev/ttyACM0 --debug
nix run .#hardware-test -- od --port /dev/ttyACM0 --debug
nix run .#hardware-test -- stir --port /dev/ttyACM0 --debug
nix run .#hardware-test -- pumps --port /dev/ttyACM0 --debug
nix run .#hardware-test -- heaters --port /dev/ttyACM0 --debug
nix run .#hardware-test -- all --port /dev/ttyACM0 --debug --report ./hardware-first-run.json
```

For a read-only rolling view of raw thermistor and photodiode values, launch
the TUI with `nix run .#run-tui` and press `m`. See the detailed
[live-monitor procedure](../testing/min-evolver-hardware-playbook.md#optional-live-sensor-monitor).

| Command | Effect | Dry safe |
| --- | --- | --- |
| `HW_STATUS_!` | metadata only | yes |
| `HW_READ_THERMISTOR,n_!` | raw 16-bit ADC read | yes |
| `HW_READ_PHOTODIODE,n_!` | raw 16-bit ADC read | yes |
| `HW_SET_OD_LED,n,level_!` | one LED PWM (0–255) | yes |
| `HW_PULSE_PUMP,n,ms_!` | one-shot pump, max 1000 ms | yes |
| `HW_PULSE_STIR,n,ms,level_!` | one-shot stir, max 1000 ms / 250 | yes |
| `HW_PULSE_HEATER,n,ms,level_!` | bounded heater, max 250 ms / 64 | limited |
| `HW_SAFE_!` | immediately disable every output | yes |

Any hardware command enters commissioning mode and suspends normal actuator
control. It expires after 15 seconds without a valid command, forcing all
outputs off. `HW_SAFE` cancels pending pulses and chemostat schedules. The OD
test checks electronic response and channel association only; it reports
`od_calibration=NOT_CALIBRATED`.

After boot, pumps, stirrers, heaters, and OD LEDs are OFF and temperature PID
is disabled. Only an explicit applied normal `temp` command enables PID. An
MP915 heater becoming hot while idle is a fault: disconnect actuator power and
inspect the driver and wiring.

For a post-flash safe-idle check, keep actuator power disconnected and run:

```bash
nix run .#hardware-test -- protocol --port /dev/ttyACM0 --debug
```

Require `temp_control=off,mode=idle` in `HW_STATUS` and a successful
`HW_SAFE`. Reset the controller, wait 30 seconds without a normal `temp`
command, then reconnect actuator power only to observe that the MP915 heaters
stay cool. See the detailed [safe-idle procedure](../testing/min-evolver-hardware-playbook.md#required-safe-idle-check-after-flashing).

The reference min-eVOLVER PCB uses A03422 N-channel low-side MOSFETs Q6 and Q8
for heaters 0 and 1. Heater control is active-high: PWM/`HIGH` energizes it and
zero duty/`LOW` is off. Do not use an active-low assumption when diagnosing or
modifying this board.
