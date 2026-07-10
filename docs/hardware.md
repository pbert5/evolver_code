# Hardware — Arduino Firmware and Device Provisioning

## Supported Arduino targets

Two board families run the MINEVOLVER firmware:

| Board | Chip | USB | Flash storage | Serial device |
|---|---|---|---|---|
| SparkFun SAMD21 Mini | ATSAMD21G18 | Native USB (CDC) | FlashStorage_SAMD (emulated EEPROM) | `/dev/ttyACM*` |
| Arduino Nano (clone) | ATmega328P + CH340 | UART via CH340 | RAM only — lost on reboot | `/dev/ttyUSB*` |

The SAMD21 is the production target. The Nano port works for development and bench testing but requires the server to re-provision the device after every power cycle (no persistent flash storage on AVR yet).

## Firmware layout

```
evolver-arduino/
  SAMD21/MINEVOLVER/   — SAMD21 target (SerialUSB, TurboPWM, FlashStorage)
  Nano/MINEVOLVER/     — Nano/AVR target (Serial, standard PWM, RAM identity)
  libraries/evolver_si — evolver serial interface library (SAMD21 only)
  libraries/PID_v1     — temperature PID
  tests/               — Python protocol tests (no hardware needed)
```

The Nano firmware avoids the `evolver_si` library (its `String input_array[50]` alone exceeds the Nano's 2 KB RAM). It uses fixed `char[]` buffers and inline field parsers instead.

**RAM budget on Nano (ATmega328P, 2 KB):** compiled firmware uses ~51% (≈1048 bytes), leaving ~1000 bytes for stack and local variables.

## Building and flashing

### First-time setup

```bash
cd evolver-arduino

# SAMD21 (SparkFun core)
nix run .#setup-arduino

# Nano / AVR
nix run .#setup-arduino-nano
```

### Build

```bash
# SAMD21
nix run .#build-firmware

# Nano
nix run .#build-firmware-nano
```

### Flash

```bash
# SAMD21 (default port /dev/ttyACM0)
PORT=/dev/ttyACM0 nix run .#upload-firmware

# Nano (default port /dev/ttyUSB0)
PORT=/dev/ttyUSB0 nix run .#upload-firmware-nano
# or override FQBN for Nano with new bootloader:
FQBN=arduino:avr:nano:cpu=atmega328 PORT=/dev/ttyUSB0 nix run .#upload-firmware-nano
```

The upload apps are interactive — they print a warning and ask for confirmation before writing to hardware.

## MEV provisioning protocol

Every MINEVOLVER device must be provisioned with a `device_id` and `owner_id` before the server will use it for experiments. The protocol runs over the same serial connection used for sensor data.

### Handshake frames

```
# Identify
server → device:  WHO_ARE_YOU_!
device → server:  MEV|<proto>|<id_or_BLANK>|<seq>|HELLO|type=minievolver,proto=<p>,fw=<v>,id=<id>,owner=<owner>|<CRC8_HEX>

# Provision (only accepted when device_id is BLANK)
server → device:  PROVISION,<device_id>,<owner_id>_!
device → server:  MEV|<proto>|<id>|<seq>|PROVISION_ACK|id=<id>,owner=<owner>|<CRC8_HEX>
              or  MEV|<proto>|<id>|<seq>|PROVISION_ERR|reason=<reason>|<CRC8_HEX>

# Clear identity (required before reprovisioning)
server → device:  CLEAR_ID_!
device → server:  MEV|<proto>|BLANK|<seq>|CLEAR_ACK|ok=true|<CRC8_HEX>
```

CRC8 is Dallas/Maxim 1-Wire (poly=`0x31`, init=`0xFF`) applied over the payload field only. See `tests/test_protocol.py` for the Python implementation and `identity.h` for the C implementation.

### Device states

| State | Meaning |
|---|---|
| `UNKNOWN` | No response, bad CRC, wrong device type, or old protocol |
| `UNPROVISIONED` | Valid MINEVOLVER firmware; identity field is `BLANK` |
| `KNOWN` | Identity present and matches server's config |
| `MISMATCH` | Identity present but doesn't match expected device_id/owner_id |

### Python API

```python
import serial, time
from evolver.serial_discovery import discover_devices, probe_port
from evolver.provisioning import ProvisioningStateMachine, ProvisioningMode, DeviceState

# Scan all ports
results = discover_devices()
for port, result in results.items():
    print(port, result.state, result.hello)

# Probe a specific port
result = probe_port('/dev/ttyUSB0')

# Full provisioning flow
with serial.Serial('/dev/ttyUSB0', 9600, timeout=4) as conn:
    time.sleep(2)  # let Arduino boot after DTR reset
    sm = ProvisioningStateMachine(mode=ProvisioningMode.AUTO)

    r = sm.identify(conn)
    if r.state == DeviceState.UNPROVISIONED:
        sm.provision(conn, device_id='nano-001', owner_id='evolver-server')

    # Verify
    r2 = sm.identify(conn)
    assert r2.state == DeviceState.KNOWN
```

`ProvisioningMode.AUTO` is for scripted use. Use `ProvisioningMode.ASK` (default) in production — it requires explicit confirmation before any identity write.

## Nano-specific limitations

- **RAM-only identity:** The Nano has no flash backend for `identity.h` (FlashStorage_SAMD is SAMD21-only). The provisioned identity lives in RAM and is lost on every power cycle. The server must re-run provisioning on each boot.
- **10-bit ADC:** The Nano's `analogRead` returns 0–1023. The SAMD21 uses 16-bit resolution (0–65535). Raw OD/temp values from a Nano will be in a different range than a SAMD21.
- **Stir PWM scaling:** The Nano uses `analogWrite` (0–255). The SAMD21 firmware uses TurboPWM (0–500). The Nano firmware scales stir values by ×5 (e.g. stir value `8` → PWM duty `40/255`). Recalibrate stir if switching from SAMD21 hardware.
- **No `evolver_si`:** The Nano firmware implements command parsing inline. It supports `od_90`, `temp`, `stir`, and `pump` — not `od_135`, `od_led`, or `lxml`.

## Running protocol tests (no hardware)

```bash
cd evolver-arduino
nix develop
pytest tests/
# or
nix flake check
```
