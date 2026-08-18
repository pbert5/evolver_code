# Hardware-testing playbook

All normal tests are dry-safe: remove liquid/vials before use. Run
`nix run .#hardware-test -- <usb|protocol|sensors|pumps|stir|heaters|all> --port /dev/ttyACM0`.

USB/protocol: expect a `MEV|2|...` reply to `WHO_ARE_YOU_!` at 9600 baud. PASS
requires protocol 2 and type `minievolver`; a malformed response is FAIL.

Thermistors: expect three non-rail readings per sleeve. Zero/full-scale or a
stuck value is WARN/FAIL; this checks electronics only and temperature remains
NOT_CALIBRATED. OD LED/photodiode testing requires firmware commands verified
against restored firmware; it must establish LED response and cross-channel
association, never OD calibration.

Pumps 0–5 and stir 0–1: the tool pulses one logical channel conservatively and
asks which physical item moved. PASS requires the same channel; none, a wrong
channel, or duplicates identify wiring/mapping faults. Stir actuation does not
prove biological mixing. Heater output tests are bounded at low duration; they
must not use normal closed-loop heating with empty sleeves. Temperature control
is NOT_TESTABLE dry and temperature calibration is NOT_CALIBRATED.

Emergency shutdown runs after every session, Ctrl-C/exception, and TUI exit:
pumps, stir, heaters and OD LEDs are commanded off. If serial is lost, the
report shows a prominent shutdown WARN; physically disconnect power before
investigation.
