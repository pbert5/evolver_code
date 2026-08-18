# min-eVOLVER Firmware, Hardware Testing, and Commissioning Playbook

This bench procedure is for a newly assembled min-eVOLVER connected over USB to
a Linux/NixOS host. It reflects `evolver_code` commit
`779f85b33a5f4d8e7e7631e8e89738d4fede1802` and `evolver-arduino` commit
`1cc0ab78bb1de8ae3423ffa4b718712d35c54f46`.

## Three separate stages

| Stage | Proves | Does not prove |
| --- | --- | --- |
| Firmware validation | Correct firmware builds, flashes, re-enumerates, answers `WHO_ARE_YOU_!`, and reports `hw_proto=1` from `HW_STATUS_!`. | A physical channel works. |
| Hardware validation | Individual sensors, output drive paths, and mappings work. | Calibration or biological readiness. |
| Commissioning | The guided end-to-end workflow runs and writes a permanent record. | OD, temperature, fluid-flow, or mixing calibration. |

**Hardware PASS is not calibration.** OD, temperature, pump flow, and actual
mixing calibration are separate tasks.

> **Warning:** If serial communication fails and you cannot confirm software
> shutdown, disconnect actuator power before investigating hardware.

Any valid hardware command enters commissioning mode. It suspends normal
controller behavior, puts temperature PID in manual mode, and the safe-state
path cancels scheduled pump activity. Pulses are non-blocking and firmware
bounded. Host cleanup attempts `HW_SAFE_!`; after a serial failure, only a
physical power disconnect can guarantee actuator power is removed.

| Safety limit | Value |
| --- | --- |
| Hardware-test idle timeout | 15 seconds without a valid HW command |
| Pump pulse | 1000 ms maximum |
| Stir pulse | 1000 ms maximum; level 250 maximum |
| Heater pulse | 250 ms maximum; level 64 maximum |
| OD LED | level 0–255 |

After 15 seconds of inactivity, firmware forces safe state: outputs off and
pending test pulses/scheduled pumps cancelled. `HW_SAFE_!` does the same
immediately. Normal control resumes only on a subsequent normal experiment
command; that transition also starts from safe state.

## Authoritative hardware map

`SAMD21/MINEVOLVER/MINEVOLVER.ino` in `evolver-arduino` is authoritative; host
documentation should mirror it.

| Component | Sleeve 0 | Sleeve 1 |
| --- | --- | --- |
| Thermistor | A0 | A1 |
| Photodiode | A2 | A3 |
| Heater | pin 2 | pin 3 |
| OD LED | pin 4 | pin 5 |
| Stir | pin 11 | pin 13 |

| Logical pump | SAMD21 pin |
| ---: | ---: |
| 0 | 6 |
| 1 | 7 |
| 2 | 8 |
| 3 | 9 |
| 4 | 10 |
| 5 | 12 |

## Before going to the bench

```bash
git switch test-hardware
git pull
git submodule update --init --recursive
nix develop -c python -m pytest tests/test_hardware.py -q
nix develop -c flake8 evolver_integrated/hardware tests/test_hardware.py
nix run .#build-firmware
```

The focused suite currently reports `19 passed`. Firmware must compile for
`SparkFun:samd:samd21_mini`. A validated build used approximately 19% flash and
22% RAM; those percentages are informative, not rigid pass criteria.

- [ ] Assembled min-eVOLVER and USB **data** cable
- [ ] Linux/NixOS host, correct branch, and initialized submodule
- [ ] No culture; no liquid is required for dry tests
- [ ] Pump tubing may remain dry for short commissioning pulses
- [ ] Actuator-power disconnect is accessible
- [ ] Operator can identify pumps 0–5 and Smart Sleeves 0–1
- [ ] Actuator power disconnected for flashing and non-actuating tests

USB powers the SAMD21/serial connection; actuator power runs physical outputs.
Flashing needs USB but not actuator power. Connect the normal supply specified
by the assembled hardware only in Phase 9; this playbook does not prescribe a
different supply rating.

## Phase 1: discover the SAMD21

```bash
ls -l /dev/ttyACM*
lsusb                 # optional
```

`/dev/ttyACM0` is common but must not be assumed. The historical USB VID:PID is
`1b4f:8d21`. With multiple ACM devices, explicitly choose the board's port in
every later command.

| Symptom | Action |
| --- | --- |
| No `/dev/ttyACM*` | Try a known data cable/USB port; reconnect and inspect `lsusb` and `dmesg \| tail`. |
| Permission denied | Add the operator to `dialout` (or the distribution's serial-device group), log out/in, and retry. |
| Multiple ACM devices | Pass `--port /dev/ttyACM<n>`; do not guess. |
| Device only appears briefly | Watch `dmesg \| tail`; inspect cable, reset, and bootloader state. |
| Port changes while flashing | Re-list `/dev/ttyACM*`; bootloader/application re-enumeration can change it. |

## Phase 2: install firmware tooling

```bash
nix run .#setup-arduino
```

This installs the `arduino:samd` and `sparkfun:samd` cores plus
`FlashStorage_SAMD` and `PID` into workspace-local Arduino CLI state. The FQBN
is `SparkFun:samd:samd21_mini`.

## Phase 3: build firmware

```bash
nix run .#build-firmware
```

PASS: successful exit and compilation of
`evolver-arduino/SAMD21/MINEVOLVER/MINEVOLVER.ino` for that FQBN.

| Failure | Remediation |
| --- | --- |
| Sketch/submodule missing | `git submodule update --init --recursive`; verify the pinned submodule revision. |
| Cores or libraries missing | Repeat `nix run .#setup-arduino`. |
| Wrong board target | Use `.#build-firmware`; do not substitute a different FQBN. |
| Persistent compiler error | Preserve output and verify both pinned revisions before changing hardware. |

## Phase 4: flash and validate firmware

Keep actuator power disconnected. Substitute the discovered port.

```bash
nix run .#upload-firmware -- --port /dev/ttyACM0
```

The upload helper uploads, waits for reset/re-enumeration, then opens the specified port at 9600 baud, sends `WHO_ARE_YOU_!`, and sends `HW_STATUS_!`. PASS requires `type=minievolver`, `proto=2`, `fw=0.2`, and `hw_proto=1`.

```text
HW|1|OK|STATUS|sleeves=2,pumps=6,fw=0.2,id=BLANK,hw_proto=1
```

| Failure | Action |
| --- | --- |
| Upload fails | Recheck cable/port, run setup, and use the bootloader's newly enumerated port if it changed. |
| Board stays in bootloader or does not re-enumerate | Reconnect/reset, inspect `dmesg \| tail`, identify the ACM port, and retry. |
| `WHO_ARE_YOU_!` timeout | Confirm the post-reset port and close other serial clients. |
| Identity has no `hw_proto` | Old firmware is running; rebuild and flash this commissioning firmware. |
| `HW_STATUS` is `ERR` | Preserve its complete reply and inspect protocol/firmware revisions before continuing. |

## Phase 5: non-actuating smoke test

```bash
nix run .#hardware-smoke -- --port /dev/ttyACM0
```

This does not command pumps, stirrers, heaters, or OD LEDs. It runs `WHO_ARE_YOU_!`, `HW_STATUS_!`, three thermistor reads for each sleeve, one photodiode read for each sleeve, then session cleanup with `HW_SAFE_!`. PASS means communication, commissioning protocol, both analog sensor classes, and a safe-state acknowledgement work. It does not prove actuator hardware.

## Phase 6: protocol test

```bash
nix run .#hardware-test -- protocol --port /dev/ttyACM0 --debug
```

PASS includes output such as:

```text
[PASS           ] controller.protocol
       expected: protocol 2 min-eVOLVER with hw_proto>=1
       observed: BLANK firmware 0.2
```

`--debug` records TX, RX, elapsed `duration_ms`, and parsed identity/status fields. Failure means do not proceed to actuator tests.

## Phase 7: sensor test

```bash
nix run .#hardware-test -- sensors --port /dev/ttyACM0 --debug
```

The tool collects three raw 16-bit ADC readings per thermistor. Rails (0 or 65535) and a very large spread are WARN; perfectly stable repeated values are allowed. As an optional cross-channel sanity check, warm Sleeve 0 gently by hand, rerun, and verify thermistor 0 changes while thermistor 1 does not show the same response; repeat for Sleeve 1.

Record `thermistor electronics: PASS` and `temperature calibration: NOT_CALIBRATED`. A rail value suggests an open/short, connector, or wiring issue—not a calibration result.

## Phase 8: OD electronics test

```bash
nix run .#hardware-test -- od --port /dev/ttyACM0 --debug
```

For each sleeve the tool turns both LEDs off, reads both photodiodes as baseline, drives the selected LED at 32, 128, then 255, reads both diodes after each level, turns that LED off, and uses session safe cleanup. It checks command acknowledgement, non-rail/stuck behavior, and whether the associated diode responds more than the opposite channel when optical geometry makes that comparison meaningful. No absolute threshold is imposed for an empty sleeve.

Record `OD LED drive: PASS`, `photodiode electronics: PASS`, `channel association: PASS` or `WARN`, and `OD calibration: NOT_CALIBRATED`. Real OD calibration needs the normal vial, cover, optical geometry, and standards.

## Phase 9: connect actuator power

- [ ] Non-actuating tests passed
- [ ] `HW_SAFE` succeeded
- [ ] All outputs are visibly inactive
- [ ] Operator knows the physical actuator-power disconnect

Now connect the normal actuator supply specified for the assembled min-eVOLVER, and keep its disconnect accessible.

## Phase 10: stir mapping

```bash
nix run .#hardware-test -- stir --port /dev/ttyACM0 --debug
```

The host pulses each stir for 500 ms at level 100, within the 1000 ms/250 firmware bounds, and prompts for the observed physical channel. Enter `0` or `1` for the sleeve that moved, `N` for none, or `S` to skip. Logical stir 0 must move Sleeve 0 and logical stir 1 must move Sleeve 1. Matching observation is PASS; none or wrong channel is FAIL; skip is SKIP.

`stir actuation PASS` does not prove mixing performance, stir-bar behavior, or RPM calibration.

## Phase 11: pump mapping

```bash
nix run .#hardware-test -- pumps --port /dev/ttyACM0 --debug
```

Each logical pump gets a conservative 500 ms pulse (firmware maximum 1000 ms), then the `number/N/S` prompt. Complete this worksheet:

| Logical pump | Expected pin | Observed physical pump | Result |
| ---: | ---: | --- | --- |
| 0 | 6 | | |
| 1 | 7 | | |
| 2 | 8 | | |
| 3 | 9 | | |
| 4 | 10 | | |
| 5 | 12 | | |

`logical 2 -> physical 2` is PASS; `logical 2 -> physical 4` is a mapping/wiring FAIL; `logical 2 -> none` is a physical-actuation FAIL. Duplicate successful physical mappings produce a WARN because mappings must be unique.

```text
command ERR
  -> protocol or firmware: retain the HW|1|ERR reply
command OK but nothing moves
  -> actuator power -> driver -> wiring -> connector -> pump
wrong pump moves
  -> wiring/mapping
```

An OK reply proves parsing and firmware drive request, not that a pump received power or moved.

## Phase 12: heater dry electrical-drive test

```bash
nix run .#hardware-test -- heaters --port /dev/ttyACM0 --debug
```

**This is not a temperature-control test or temperature calibration. Do not run normal PID heating against an empty sleeve.** The host requests 250 ms at level 32; firmware limits are 250 ms and level 64. The heater driver is active-low: safe/off writes the corresponding high/off value. A short dry pulse may have no meaningful physical indication, so PASS primarily means the bounded drive command was acknowledged and cleanup returns safely off. Use additional measurement equipment only under an approved electrical test procedure.

Record `heater electrical drive: PASS`, `closed-loop temperature control: NOT_TESTABLE`, and `temperature calibration: NOT_CALIBRATED`. Do not casually increase duration or level after failure; inspect power, driver, wiring, and safe-state behavior first.

## Phase 13: emergency shutdown verification

Every test session automatically sends `HW_SAFE_!` during cleanup. Confirm `safety.shutdown` and an acknowledgement such as:

```text
HW|1|OK|SAFE|outputs=off
```

Verify pumps, stirrers, heaters, and OD LEDs are off; pending test pulses and pump schedules are cancelled. Hardware-test inactivity also triggers the 15-second safe state. Do not intentionally exercise that watchdog with heaters active; explicit `HW_SAFE_!` cleanup is the supported safe test.

## Phase 14: full hardware test

Only after individual stages are understood:

```bash
nix run .#hardware-test -- all \
  --port /dev/ttyACM0 \
  --debug \
  --report ./hardware-first-run.json
```

`all` runs USB, protocol, both sensor tests, both OD tests, two stirs, six pumps, and two heater prompts. Status values are `PASS`, `FAIL`, `WARN`, `SKIP`, `NOT_TESTABLE`, and `NOT_CALIBRATED`: matching pump is PASS, weak OD association is WARN, declined heater is SKIP, unconfirmed actuator before the answer is NOT_TESTABLE, and calibration remains NOT_CALIBRATED.

## Phase 15: formal commissioning

```bash
nix run .#commission-evolver -- \
  --operator NAME \
  --port /dev/ttyACM0
```

This recorded workflow asks for dry-actuation confirmation, runs the same `all` layer, and writes `commissioning/report.json` by default. `--report PATH` selects a destination; reports never overwrite an existing file, instead receiving a UTC timestamp suffix. JSON records device identity as supplied by `--device-id` (or `unknown`), port, operator, timestamps, component results, observed mappings, protocol/firmware debug replies where available, and calibration status.

`--skip-flash` only suppresses the firmware reminder; it does not validate a board. `--skip-heaters` removes heater results after the all-test run. `--resume PATH` currently reads and identifies a prior report before running a fresh workflow; it does not skip, merge, or alter new results. Preserve both reports.

## Final commissioning acceptance checklist

```text
Controller
[ ] USB detected
[ ] WHO_ARE_YOU PASS
[ ] fw=0.2
[ ] proto=2
[ ] hw_proto=1
[ ] HW_STATUS PASS
[ ] HW_SAFE PASS

Smart Sleeve 0
[ ] thermistor electronics PASS
[ ] photodiode electronics PASS
[ ] OD LED PASS
[ ] OD channel association PASS
[ ] stir mapping PASS
[ ] heater drive PASS or intentionally SKIPPED

Smart Sleeve 1
[ ] thermistor electronics PASS
[ ] photodiode electronics PASS
[ ] OD LED PASS
[ ] OD channel association PASS
[ ] stir mapping PASS
[ ] heater drive PASS or intentionally SKIPPED

Pumps
[ ] pump 0 mapping PASS
[ ] pump 1 mapping PASS
[ ] pump 2 mapping PASS
[ ] pump 3 mapping PASS
[ ] pump 4 mapping PASS
[ ] pump 5 mapping PASS

Safety
[ ] all outputs off after tests
[ ] HW_SAFE acknowledged
[ ] no actuator unexpectedly resumes
[ ] commissioning report saved

Still required before real biological use
[ ] pump flow calibration
[ ] OD calibration
[ ] temperature calibration
[ ] actual stir/mixing validation
[ ] tubing/fluidics configured
[ ] experimental configuration verified
```

## Troubleshooting

For no ACM device, run `lsusb` and `dmesg | tail`, then check USB data cable, port, and board reset state. For permissions, use `dialout` or the relevant serial-device group and start a new login session. For a busy port, identify the owner with `lsof /dev/ttyACM0` and stop it before testing.

`WHO_ARE_YOU_!` working while `HW_STATUS_!` fails normally indicates older or incompatible commissioning firmware; flash the pinned revision. Read errors as `HW|1|ERR|OPERATION|reason=...` and retain operation/reason in the bench record. `invalid_command_or_arguments` means firmware rejected syntax, range, or argument count.

| Observation | Diagnosis branch |
| --- | --- |
| Thermistor rail | Inspect open/short, sleeve connector, and wiring. |
| Photodiode does not change | Check LED wiring, PD wiring, sleeve mapping, optical geometry, and acknowledged LED command. |
| Wrong physical pump | Wiring/mapping issue, not a successful mapping result. |
| Pump ACK but no movement | Protocol success differs from physical actuation: inspect supply, driver, wiring, connector, then pump. |
| Stir does not move | Inspect power, driver, sleeve wiring/connector, and physical stir assembly. |
| Heater test failure | Do not increase the bounded pulse; inspect power, driver, wiring, and safe-state behavior. |
| Serial dies during actuation | Disconnect actuator power immediately if safe state cannot be confirmed. |

## Debugging appendix: commissioning protocol

Commands end in `_!`; responses are `HW|1|OK|...` or `HW|1|ERR|...`. Firmware also accepts `HW_ALL_OFF_!` as an alias for `HW_SAFE_!`, but host tools use `HW_SAFE_!`.

| Command | Arguments/range | Response operation | Side effect/safety |
| --- | --- | --- | --- |
| `HW_STATUS_!` | none | `STATUS` | Metadata only. |
| `HW_READ_THERMISTOR,n_!` | `n=0..1` | `THERMISTOR` | Raw ADC read; enters test mode. |
| `HW_READ_PHOTODIODE,n_!` | `n=0..1` | `PHOTODIODE` | Raw ADC read; enters test mode. |
| `HW_SET_OD_LED,n,l_!` | `n=0..1`, `l=0..255` | `SET_OD_LED` | Sets one LED; test mode stays active. |
| `HW_PULSE_PUMP,n,ms_!` | `n=0..5`, `ms=1..1000` | `PULSE_PUMP` | Non-blocking bounded pulse. |
| `HW_PULSE_STIR,n,ms,l_!` | `n=0..1`, `ms=1..1000`, `l=1..250` | `PULSE_STIR` | Non-blocking bounded pulse. |
| `HW_PULSE_HEATER,n,ms,l_!` | `n=0..1`, `ms=1..250`, `l=1..64` | `PULSE_HEATER` | Active-low bounded electrical pulse. |
| `HW_SAFE_!` | none | `SAFE` | Immediate output-off safe state; cancels pulses/schedules. |

Examples:

```text
HW_STATUS_!
HW|1|OK|STATUS|sleeves=2,pumps=6,fw=0.2,id=BLANK,hw_proto=1

HW_PULSE_PUMP,3,500_!
HW|1|OK|PULSE_PUMP|channel=3,pin=9,duration_ms=500

HW_READ_THERMISTOR,0_!
HW|1|OK|THERMISTOR|channel=0,value=31284
```
