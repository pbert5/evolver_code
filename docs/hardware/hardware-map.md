# Hardware map

The map is defined in `evolver_integrated.hardware.model.HARDWARE_MAP` and is
based on the historical checked-in SAMD21 notes; firmware source is currently
absent from this checkout, so verify it after restoring the Arduino tree.

| Logical component | Firmware pin |
| --- | --- |
| Sleeve 0 thermistor / OD / heater / LED / stir | A0 / A2 / 2 / 4 / 11 |
| Sleeve 1 thermistor / OD / heater / LED / stir | A1 / A3 / 3 / 5 / 13 |
| Pumps 0–5 | 6, 7, 8, 9, 10, 12 |
