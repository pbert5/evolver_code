# Arduino / SAMD21 Hardware Notes

Findings from first live hardware test (2026-07-14) with SparkFun SAMD21 Mini
connected to `/dev/ttyACM0`.

## Device Detection

- USB ID: `1b4f:8d21` (SparkFun SFE SAMD21)
- Appears as `/dev/ttyACM0`
- User must be in `dialout` group (NixOS: add via `users.users.ash.extraGroups`)
- `arduino-cli board list` shows "Unknown" until SparkFun core is installed

## Core Installation

`setup-arduino` must install **both** cores — SparkFun SAMD depends on Arduino SAMD for
its ARM toolchain tools:

```bash
arduino-cli core install sparkfun:samd arduino:samd
```

Installing only `sparkfun:samd` leaves the dependency unresolved and `arduino-cli compile`
fails with "platform not installed" even though `arduino-cli core list` shows it present.

## Correct FQBN

The SparkFun SAMD21 Mini board ID is **`SparkFun:samd:samd21_mini`**, not
`sparkfun:samd:sparkfun_samd21_mini` (which was the wrong default in flake.nix).

## FlashStorage_SAMD 1.3.2 API Break

`identity.h` was written against an older FlashStorage_SAMD API. Version 1.3.2
changed both `read` and `write` signatures:

| Old | New |
|---|---|
| `T obj = flash.read()` | `flash.read(T& out)` |
| `flash.write(const T& v)` | `flash.write(T& v)` (non-const ref) |

Fixed in `SAMD21/MINEVOLVER/identity.h`:
- `_mev_flash_read`: `mev_flash.read(*out)` instead of `*out = mev_flash.read()`
- `_mev_flash_write`: copy to local `tmp` before calling `mev_flash.write(tmp)`

## Nix App Sandbox Limitation

`nix run .#build-firmware` runs arduino-cli inside a Nix-built wrapper that does **not**
see cores installed by `nix run .#setup-arduino` into `~/.arduino15`. The two apps share
`~/.arduino15` as the data dir when invoked directly, but the build app's FHS env can
diverge. Work around: invoke `arduino-cli` directly from the dev shell rather than via
`nix run .#build-firmware` until the flake apps are reworked to use a pinned, hermetic
arduino-cli data directory.

## Serial Protocol Test

After flashing, the WHO_ARE_YOU handshake works:

```
→ WHO_ARE_YOU_!
← MEV|2|BLANK|1|HELLO|type=minievolver,proto=2,fw=0.1,id=BLANK,owner=BLANK|66
```

Device responds at 9600 baud, ~2 s after USB enumeration (bootloader + sketch init).

## Integration Implications

When `integrated_evolver` gains a hardware service (`evolver-hardwared`):
- It should detect SAMD21 by USB VID:PID `1b4f:8d21` or by probing `/dev/ttyACM*`
  with the WHO_ARE_YOU handshake
- Baud rate: 9600
- Identity provisioning flow is defined in `evolver-arduino/CLAUDE.md`
- The hardware service owns the serial port exclusively; other services talk to it
  via the control plane, not directly
