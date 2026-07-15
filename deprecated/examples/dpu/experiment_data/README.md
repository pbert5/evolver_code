# DPU Experiment Data — File Formats

All files are plain CSV. No header row. Written by `eVOLVER.save_data()`.

## Column format

```
elapsed_time_hours, value
```

`elapsed_time` is calculated as `(time.time() - start_time) / 3600` and rounded
to 4 decimal places.

## File naming

```
{EXP_NAME}/
  OD/       vial{N}_OD.txt       — calibrated OD (dimensionless)
  temp/     vial{N}_temp.txt     — temperature (°C)
  od_90/    vial{N}_od_90.txt    — raw 90° ADC value (16-bit integer as float)
  od_135/   vial{N}_od_135.txt   — raw 135° ADC value
  pump_log/ vial{N}_pump_log.txt — influx pump time per event (seconds)
  gr/       vial{N}_gr.txt       — calculated growth rate (h⁻¹)
```

## Example values — turbidostat at OD threshold 0.4

### vial0_OD.txt
Sawtooth pattern: OD rises from ~0.1 (post-dilution) to ~0.4 (threshold),
then drops sharply after a pump event.

```
0.0,0.048       ← experiment start, inoculation
0.0556,0.103    ← ~20 min, early log phase
0.1278,0.335    ← approaching threshold
0.1389,0.393    ← triggers dilution
0.1444,0.098    ← post-dilution, OD drops 4×
0.2389,0.391    ← approaching threshold again
0.2444,0.101    ← next dilution
```

### vial0_temp.txt
Steady at setpoint with ±0.1 °C noise.

```
0.0,29.85
0.0056,30.02
```

### vial0_gr.txt
One value written per dilution event, calculated over the preceding growth window.
Units: h⁻¹. Typical yeast: 0.5–0.7 h⁻¹.

```
0.1444,0.5823   ← growth rate from t=0 to first dilution
0.2444,0.5901   ← growth rate for second growth window
```

### vial0_pump_log.txt
One row per pump event. Value is influx pump on-time in seconds.
`time_in = volume_mL / pump_rate_mLs`

```
0.1444,7.5      ← 7.5 s influx = 0.75 mL/s × 10 s ≈ 7.5 mL added
0.2444,7.5
```
