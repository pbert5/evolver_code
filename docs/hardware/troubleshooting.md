# Troubleshooting

No `/dev/ttyACM*`: check cable/power and bootloader state. Permission denied:
add the operator to `dialout`. Multiple ports: pass `--port`; do not guess.
Upload failures often mean the SAMD21 bootloader port changed. A build that does
not answer `WHO_ARE_YOU_!` is not a validated min-eVOLVER firmware.

For a bad handshake, use 9600 baud and ensure no other process owns the port.
If a pump/stir command is accepted but the wrong item moves, record the observed
mapping and correct wiring. A non-changing photodiode suggests LED/sleeve
wiring; zero/full-scale thermistors suggest an electrical fault. On heater or
serial failures, inspect the reported safe-state WARN and disconnect power if
shutdown could not be confirmed.
