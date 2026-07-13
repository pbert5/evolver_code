# Arduino Serial Protocol — Frame Examples

Serial port: `/dev/ttyAMA0`, 9600 baud, 1s timeout, 0.1s inter-command delay.

## Frame structure

```
Outgoing (RPi → Arduino):
  {param}{cmd_char},{val0},{val1},...,{valN},_!

Incoming (Arduino → RPi):
  {param}{resp_char},{val0},{val1},...,{valN},end
```

Command characters:
- `r` — recurring (scheduled every `broadcast_timing` seconds)
- `i` — immediate (one-shot, highest priority)
- `a` — acknowledge (confirms Arduino may execute the command)

Response characters:
- `b` — data response (new sensor readings)
- `e` — echo response (settings applied, echoes back written values)

---

## OD (optical density) — 90° detector

`fields_expected_outgoing: 2` — one value (integration time) + command char  
`fields_expected_incoming: 17` — response char + 16 vial ADC values

### RPi → Arduino (set integration time, recurring)
```
od_90r,1000,_!
```

### Arduino → RPi (data broadcast, 16 vial readings)
```
od_90b,60584,59787,64403,56648,56681,56924,58908,57293,57091,56770,58489,64598,59863,58719,58737,59081,end
```

### RPi → Arduino (acknowledge, allowing Arduino to proceed)
```
od_90a,,_!
```

---

## OD — 135° detector

Same frame shape as `od_90`, different photodetector angle.

### RPi → Arduino
```
od_135r,1000,_!
```

### Arduino → RPi
```
od_135b,60434,62904,61799,62387,62238,63049,63502,61271,61481,62159,63086,63885,63998,62465,62211,62107,end
```

---

## Temperature

`fields_expected_outgoing: 17` — command char + 16 set-point DAC values  
`fields_expected_incoming: 17` — response char + 16 ADC readings

The DAC set-point `4095` is the maximum value (heater fully on during calibration);
during experiments the value is set per-vial to reach a target temperature.

### RPi → Arduino (set DAC values for all vials)
```
tempr,4095,4095,4095,4095,4095,4095,4095,4095,4095,4095,4095,4095,4095,4095,4095,4095,_!
```

### Arduino → RPi (raw ADC readings ≈ 1880 at ~30 °C)
```
tempb,1883,1874,1878,1880,1888,1876,1866,1871,1884,1890,1873,1883,1882,1880,1877,1869,end
```

---

## Stirring

`fields_expected_outgoing: 17` — command char + 16 PWM values (0–10)  
`fields_expected_incoming: 17` — echo response + 16 echoed values

Stir speed `8` is typical for active culture (maximum is 10).

### RPi → Arduino
```
stirr,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,_!
```

### Arduino → RPi (echo confirms values written)
```
stire,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,end
```

---

## Pump

`fields_expected_outgoing: 49` — command char + 48 pump-time values  
`fields_expected_incoming: 49` — echo response + 48 echoed values

48 values = 16 vials × 3 pumps (influx media, influx efflux, waste).  
Values are time in seconds × 10 (so `75` = 7.5 seconds). `0` = pump off.

### RPi → Arduino (pump vial 0 influx for 7.5 s, all others off)
```
pumpi,75,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,_!
```

### Arduino → RPi (echo)
```
pumpe,75,0,0,0,...,0,end
```

---

## OD LED brightness (od_led)

Controls LED current for all 16 OD emitters simultaneously.  
`4095` = maximum brightness; reduce if detector saturates.

### RPi → Arduino
```
od_ledr,4095,4095,4095,4095,4095,4095,4095,4095,4095,4095,4095,4095,4095,4095,4095,4095,_!
```

---

## Error conditions

If the response terminator `end` is missing, the server raises `EvolverSerialError`:
```
Error: Response did not have valid serial communication termination string!
    Expected: end
    Found: \r\n
```

If the response character is neither `b` nor `e`:
```
Error: Incorrect response character.
    Expected: b
    Found: x
```
