# Arduino Serial Protocol — Timing and Frame Diagram

## Transaction sequence per parameter

```
RPi (evolver_server)                          Arduino (miniEvolver firmware)
        │                                              │
        │  ① Write command frame                       │
        │──── od_90r,1000,_! ─────────────────────────►│
        │                                              │
        │  ② Arduino echoes or responds with data      │
        │◄─── od_90b,60584,59787,...,41058,end ────────│
        │                                              │
        │  ③ RPi sends acknowledge (Arduino may proceed│
        │──── od_90a,,_! ─────────────────────────────►│
        │                                              │
        │  (inter-command delay: 0.1 s)                │
        │                                              │
        │  ④ Next parameter (od_135, temp, stir, …)    │
        │──── od_135r,1000,_! ────────────────────────►│
        │  ...                                         │
```

## Encoding rules

```
Outgoing frame:   {param}{cmd_char},{val0},{val1},...,{valN},_!
                  └────┬────┘└──┬──┘└────────────────────────┘
                       │        │   N = fields_expected_outgoing - 1
                  param name  r/i/a  (N values, comma-separated)
                  (no space)         (trailing comma before _!)

Incoming frame:   {param}{resp_char},{val0},{val1},...,{valN},end
                  └────┬────┘└──┬───┘└─────────────────────────┘
                       │        │   N = fields_expected_incoming - 1
                  param name   b/e   (b = data, e = echo)
```

## Field counts by parameter

```
Parameter   fields_out  fields_in   Notes
─────────── ──────────  ─────────── ──────────────────────────────────────
od_90       2           17          1 value (timing) + cmd; b + 16 ADC
od_135      2           17          same as od_90
od_led      17          17          cmd + 16 DAC values; e + 16 echoed
temp        17          17          cmd + 16 DAC values; b + 16 ADC
stir        17          17          cmd + 16 PWM values; e + 16 echoed
pump        49          49          cmd + 48 pump times; e + 48 echoed
lxml        17          17          cmd + 16 DAC values; e + 16 echoed
```

## Immediate vs recurring commands

```
Command type   char   When used
─────────────  ─────  ──────────────────────────────────────────────────
recurring      r      Scheduled every broadcast_timing (20 s). Placed in
                      command_queue by the broadcast loop. Cleared before
                      each new broadcast cycle (clear_broadcast()).
immediate      i      One-shot. Inserted at front of command_queue with
                      highest priority. Used for pump commands from DPU.
acknowledge    a      Sent after receiving data from Arduino to signal that
                      the RPi has read the response and Arduino may proceed.
```

## Data extraction from incoming frame

```python
# From evolver_server.py serial_communication():
response = serial_connection.readline().decode('UTF-8')
# response = "od_90b,60584,59787,...,41058,end\n"

returned_data = response[len(param) : -len('end\n')-1].split(',')
# returned_data = ['b', '60584', '59787', ..., '41058']
# returned_data[0]  → response character ('b' = data, 'e' = echo)
# returned_data[1:] → 16 sensor values as strings
```

## Example: full broadcast cycle with one pump command

```
t=0.00s   ┌─ od_90r,1000,_! ──────────────────────────────────► Arduino
           │◄─ od_90b,60584,...,41058,end ───────────────────── Arduino
           │─ od_90a,,_! ──────────────────────────────────────► Arduino
           │  [0.1s delay]
           │─ od_135r,1000,_! ─────────────────────────────────► Arduino
           │◄─ od_135b,60434,...,62107,end ──────────────────── Arduino
           │─ od_135a,,_! ─────────────────────────────────────► Arduino
           │  [0.1s delay]
           │─ tempr,3012,...,3012,_! ───────────────────────────► Arduino
           │◄─ tempb,1883,...,1869,end ──────────────────────── Arduino
           │─ tempa,,,,,,,,,,,,,,,,,_! ─────────────────────────► Arduino
           │  [0.1s delay]
           │─ stirr,8,...,8,_! ────────────────────────────────► Arduino
           │◄─ stire,8,...,8,end ────────────────────────────── Arduino
           │─ stira,,,,,,,,,,,,,,,,,_! ─────────────────────────► Arduino
t≈0.5s    └─ emit('broadcast', data) ───────────────────────── DPU (socket.io)

t≈0.5s       DPU turbidostat logic: vial 0 OD=0.393 > threshold 0.4
             DPU emit('command', {param:'pump', value:[75,0,...,0]}) → server

t≈0.5s    ┌─ pumpi,75,0,...,0,_! ────────────── IMMEDIATE ──────► Arduino
           │◄─ pumpe,75,0,...,0,end ─────────────────────────── Arduino
           └─ pumpa,,,,...,,,_! ────────────────────────────────► Arduino

t=20.00s  (next broadcast cycle begins)
```
