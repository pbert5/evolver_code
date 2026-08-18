# Troubleshooting

No `/dev/ttyACM*`: check cable/power and bootloader state. Permission denied:
add the operator to `dialout`. Multiple ports: pass `--port`; do not guess.
Upload failures often mean the SAMD21 bootloader port changed. A build that does
not answer `WHO_ARE_YOU_!` and `HW_STATUS_!` with `hw_proto=1` is not a
validated commissioning min-eVOLVER firmware.

For a bad handshake, use 9600 baud and ensure no other process owns the port.
If a pump/stir command is accepted but the wrong item moves, record the observed
mapping and correct wiring. A non-changing photodiode suggests LED/sleeve
wiring; zero/full-scale thermistors suggest an electrical fault. On heater or
serial failures, inspect the reported safe-state WARN and disconnect power if
shutdown could not be confirmed. Firmware commissioning mode automatically
times out after 15 seconds; it is not a substitute for disconnecting power when
serial communication is lost.

An MP915 heater that is warm while the controller is idle is an immediate fault
condition. Disconnect actuator power first. With USB still connected, confirm
`HW_STATUS_!` reports `temp_control=off,mode=idle` and that `HW_SAFE_!` is
acknowledged; do not send a normal `temp` command or extend a heater test
pulse. Then inspect Q6/Q8—the A03422 N-channel, low-side heater MOSFETs—plus
their gate and heater wiring. A software status reply does not measure heater
voltage/current.
