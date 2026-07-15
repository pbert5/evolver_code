# Calibration Workflow Diagrams

## Temperature calibration

```
Goal: map raw ADC value → °C for each of 16 vials

Step 1: Physical setup
  ┌─────────────────────────────────────┐
  │  Place reference thermometer in     │
  │  each vial (or one representative). │
  │  Set temp DAC to 4095 (max).        │
  └───────────────┬─────────────────────┘
                  │
Step 2: Collect raw data (DPU calibrate.py)
  ┌─────────────────────────────────────────────────────┐
  │  At each target temperature (e.g., 25, 30, 37 °C): │
  │    record reference temp (°C)                       │
  │    record ADC reading from broadcast (temp field)   │
  │                                                     │
  │  Typical ADC range: ~1860 (37°C) → ~1900 (25°C)    │
  └───────────────┬─────────────────────────────────────┘
                  │
Step 3: Linear fit (per vial)
  ┌───────────────────────────────────────────────┐
  │  temp_C = slope × ADC + intercept             │
  │                                               │
  │  Typical slope:     -0.028 to -0.030 °C/ADC  │
  │  Typical intercept:  81 to 87 °C              │
  │                                               │
  │  R² should be > 0.999                         │
  └───────────────┬───────────────────────────────┘
                  │
Step 4: Save to server calibrations.json + export to DPU temp_cal.json
```

## OD calibration (sigmoid fit)

```
Goal: map raw ADC → OD (optical density) for each vial

Step 1: Prepare standard dilution series
  ┌─────────────────────────────────────────────────────┐
  │  16 cuvettes (or use 16 vials directly):            │
  │  OD600 reference values:                            │
  │    0, 0.077, 0.139, 0.197, 0.270, 0.345,           │
  │    0.430, 0.445, 0.495, 0.600, 0.760, 0.908,       │
  │    0.984, 1.176, 1.720, 2.156                       │
  └───────────────┬─────────────────────────────────────┘
                  │
Step 2: Collect raw ADC readings (3 readings per sample per vial)
  ┌───────────────────────────────────────────────────────────┐
  │  At each OD standard:                                     │
  │    read od_90 and od_135 from broadcast (3× per vial)    │
  │                                                           │
  │  High OD (dense culture) → lower ADC (more light blocked) │
  │  Low OD (clear media)    → higher ADC (~60000–65000)     │
  └───────────────┬───────────────────────────────────────────┘
                  │
Step 3: Sigmoid fit (per vial)
  ┌──────────────────────────────────────────────────────────────┐
  │  OD = a / (1 + exp(-c × (ADC - b))) + d                    │
  │                                                              │
  │  Fitted on DPU using scipy.optimize.curve_fit               │
  │                                                              │
  │  Parameters (vial 0 example):                               │
  │    a = 29432  (amplitude)                                   │
  │    b = 63297  (inflection point ADC)                        │
  │    c = 1.715  (steepness, 1/ADC units)                     │
  │    d = -0.636 (offset)                                      │
  │                                                              │
  │  Valid range: OD 0.05 – 1.2 (sigmoid flattens outside this) │
  └───────────────┬──────────────────────────────────────────────┘
                  │
Step 4: Save to server calibrations.json + export to DPU od_cal.json

ADC vs OD curve shape (schematic):

  ADC
  65000 │  ●●●                                        (blank/water)
        │      ●●●
  55000 │          ●●●
        │              ●●●
  45000 │                  ●●                         (OD ~0.5)
        │                     ●
  40000 │                      ●●●
        │                         ●●●
  35000 │                             ●●●             (OD ~1.5)
        │
        └────────────────────────────────── OD600
         0    0.2   0.5   1.0   1.5   2.0
```

## Pump calibration

```
Goal: determine flow rate (mL/s) for each of 48 pumps

Step 1: Run pump for known time, weigh output
  ┌──────────────────────────────────────────────────┐
  │  For each pump:                                  │
  │    tare collection vessel                        │
  │    run pump for 10 s via DPU setParam command    │
  │    weigh output (water ≈ 1 g/mL)                 │
  │    rate = mass / time = mL/s                     │
  └───────────────┬──────────────────────────────────┘
                  │
Step 2: Constant fit (uniform rate assumption)
  ┌──────────────────────────────────────────────────────┐
  │  48 coefficients — one per pump                      │
  │  Typical rate: 0.60 – 0.90 mL/s                     │
  │  Example: 0.75 mL/s for all pumps (well-matched set) │
  └───────────────┬──────────────────────────────────────┘
                  │
Step 3: Usage in turbidostat
  ┌────────────────────────────────────────────────────────────┐
  │  target volume: volume_to_add (mL)                        │
  │  pump time: time_in = volume_to_add / pump_cal[vial_idx]  │
  │                                                           │
  │  Example: add 7.5 mL using vial 0 influx pump            │
  │    time_in = 7.5 mL / 0.75 mL/s = 10 s                  │
  │    Arduino command value = 10 × 10 = 100 (in 0.1 s units)│
  └────────────────────────────────────────────────────────────┘
```

## Calibration data lifecycle

```
Experiment bench                DPU (calibrate.py)         Server (RPi)
      │                               │                          │
      │  serial dilutions / temps     │                          │
      │──────────────────────────────►│                          │
      │                               │  raw readings via        │
      │                               │  on_broadcast            │
      │                               │◄─────────────────────────│
      │                               │                          │
      │                               │  curve_fit / linregress  │
      │                               │  ─────────────────────   │
      │                               │                          │
      │                               │  POST calibration to     │
      │                               │  server                  │
      │                               │─────────────────────────►│
      │                               │                          │  writes
      │                               │                          │  calibrations.json
      │                               │                          │
      │                               │  GET active calibration  │
      │                               │◄─────────────────────────│
      │                               │                          │
      │                               │  write od_cal.json       │
      │                               │  write temp_cal.json     │
      │                               │  write pump_cal.json     │
      │                               │  ─────────────────────   │
      │                               │                          │
      │                         [experiment directory]           │
      │                         od_cal.json                      │
      │                         temp_cal.json                    │
      │                         pump_cal.json                    │
```
