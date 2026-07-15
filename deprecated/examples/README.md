# eVOLVER Examples

Annotated reference data and diagrams showing the exact formats produced and consumed
at each layer of the eVOLVER stack.

```
arduino/          Raw serial frames between RPi and Arduino firmware
evolver_server/   socket.io broadcast payload; server console output
calibration/      Calibration data in both server and DPU formats
dpu/              Experiment output files written by the DPU
commissioning/    Device identity config and provisioning log
diagrams/         ASCII interaction and workflow diagrams
```

## Data flow summary

```
Arduino ──serial──► evolver_server ──socket.io broadcast──► DPU
                         │                                    │
                  calibrations.json                   od_cal.json
                  conf.yml                            temp_cal.json
                  evolver-config.json                 experiment_data/
```

All ADC values from OD and temperature sensors are 16-bit unsigned integers
(0–65535). The server collects 3 readings per vial per broadcast cycle and
returns the raw list; the DPU applies calibration fits to convert them to
physical units.

## 16-vial layout

Vials are numbered 0–15. Every parameter array has exactly 16 elements (one
per vial) plus one leading command/response character — 17 fields total for
sensor and actuator parameters.
