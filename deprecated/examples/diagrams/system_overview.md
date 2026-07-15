# eVOLVER System Overview — Interaction Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  miniEvolver hardware (Arduino Mega)                            │
│                                                                 │
│  ┌───────────┐  ┌───────────┐  ┌──────────┐  ┌────────────┐   │
│  │ OD LEDs   │  │ OD detec- │  │  Temp    │  │  Peristal- │   │
│  │ (16×)     │  │ tors 90°  │  │  RTDs    │  │  tic pumps │   │
│  │           │  │ + 135°    │  │  + heaters│  │  (48×)     │   │
│  └─────┬─────┘  └─────┬─────┘  └────┬─────┘  └─────┬──────┘   │
│        │              │              │               │          │
│        └──────────────┴──────────────┴───────────────┘          │
│                                      │                          │
│                                 ADC / DAC                       │
│                                 16-bit                          │
└──────────────────────────────────────┼──────────────────────────┘
                                       │ serial / UART
                                       │ 9600 baud, /dev/ttyAMA0
                                       │
┌──────────────────────────────────────┼──────────────────────────┐
│  Raspberry Pi (evolver server)        │                          │
│                                       │                          │
│  ┌───────────────────────────────────▼──────────────────────┐   │
│  │  evolver_server.py                                        │   │
│  │                                                           │   │
│  │  serial_communication()      ← sends command frames      │   │
│  │                              → receives data frames       │   │
│  │                                                           │   │
│  │  broadcast()  every 20 s:                                 │   │
│  │    run_commands() → collects od_90, od_135, temp          │   │
│  │    emit('broadcast', {data: {...}, config: {...}})         │   │
│  └────────────────────────────────────────────────────────── ┘   │
│                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐   │
│  │ conf.yml       │  │ calibrations.  │  │ evolver-config.  │   │
│  │ (params,       │  │ json           │  │ json             │   │
│  │  serial conf)  │  │ (cal fits)     │  │ (device ID)      │   │
│  └────────────────┘  └────────────────┘  └──────────────────┘   │
│                                                                  │
│  socket.io server  port 8081  namespace /dpu-evolver             │
└──────────────────────────────────────────────────────────────────┘
                           │
                           │ TCP socket.io  (LAN / localhost)
                           │ namespace: /dpu-evolver
                           │
┌──────────────────────────┼───────────────────────────────────────┐
│  Workstation (DPU)        │                                       │
│                           │                                       │
│  ┌────────────────────────▼───────────────────────────────────┐  │
│  │  eVOLVER.py — EvolverNamespace(BaseNamespace)              │  │
│  │                                                            │  │
│  │  on_broadcast(data):                                       │  │
│  │    transform_data()   ← apply sigmoid / linear cal fits   │  │
│  │    save_data()        → vialN_OD.txt, vialN_temp.txt, …   │  │
│  │    custom_functions() → turbidostat / chemostat / growth   │  │
│  │      │                                                     │  │
│  │      └─► setParam('pump', [...]) ──► emit('command', …)   │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌────────────────┐  ┌─────────────────┐  ┌──────────────────┐   │
│  │ od_cal.json    │  │ temp_cal.json   │  │ pump_cal.json    │   │
│  │ (sigmoid coef) │  │ (linear coef)   │  │ (mL/s rates)     │   │
│  └────────────────┘  └─────────────────┘  └──────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  experiment_data/                                            │ │
│  │    vial0_OD.txt   vial0_temp.txt   vial0_pump_log.txt       │ │
│  │    vial0_gr.txt   …                                         │ │
│  └──────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
```

## Key socket.io events

| Direction        | Event              | Payload                              |
|------------------|--------------------|--------------------------------------|
| server → DPU     | `broadcast`        | `{data, config, ip, timestamp}`      |
| server → DPU     | `commandbroadcast` | echo of last `command` received      |
| server → DPU     | `config`           | full `evolver_conf` dict             |
| DPU → server     | `command`          | `{param, value, recurring, …}`       |
| DPU → server     | `getlastcommands`  | (empty) — requests current config    |
| server → DPU     | `calibration`      | single calibration entry             |
| server → DPU     | `activecalibrations` | list of active calibration names   |

## Broadcast cycle (every 20 s, configurable via `broadcast_timing`)

```
t=0s    run_commands():
          od_90  → serial → Arduino → return 16 ADC values
          od_135 → serial → Arduino → return 16 ADC values
          temp   → serial → Arduino → return 16 ADC values
          stir   → serial → Arduino → echo (no data returned)

t≈0.5s  emit('broadcast', broadcast_data) to all connected DPU clients

t≈0.5s  DPU on_broadcast():
          calibration lookup
          OD / temp conversion
          feedback logic (turbidostat / chemostat)
          if pump needed: emit('command', pump_data) back to server

t≈0.5s  server on_command():
          insert pump into command_queue as IMMEDIATE
          next cycle: pump fires before recurring reads
```
