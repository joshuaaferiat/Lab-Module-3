# Module 3 Part 8: Project Cleanup and C3 Checkpoint

This file captures the final organization and verification steps for the TEC manual-control lab.

## Part 1: TEC wiring and pre-power checklist

Completed before TEC power was applied.

| Item | Value Or Observation |
| --- | --- |
| Arduino board and port | Arduino Uno; `/dev/cu.usbmodem1101` (macOS), `COM4` (Windows) |
| Thermistor pin | A0 |
| H-bridge control pins | 9 and 10 |
| PWM starts at zero? | Yes |
| Module 2 motor test completed with TEC disconnected? | Yes |
| High-current leads are 18 AWG? | Yes |
| Prepared TEC and thermal-switch wiring inspected? | Yes |
| Heat exchanger connected to 12 V and operating? | Yes |
| Power supply voltage | 12 V |
| Power supply current limit | 10 A |
| Thermal cutoff identified? | Yes; normally closed thermal switch in series with the TEC, 65 °C cutoff |
| Instructor check complete? | Yes |

Wiring: power-supply V+/V- connect directly to H-bridge B+/B-. On the terminal bus, H-bridge M+ connects to one thermal-switch lead, the other thermal-switch lead connects to TEC+, and TEC- connects to H-bridge M-, so opening the thermal switch interrupts TEC current. The heat exchanger (pump and fans) is powered directly from the 12 V supply.

## Part 2: First manual sketch - fixed direction

Sketch: `arduino/tec_manual_fixed_direction/tec_manual_fixed_direction.ino` (9600 baud).

Signal paths:

- A0 thermistor -> average of 200 ADC readings -> temperature (Beta equation, 100 kOhm divider, B = 4540 K)
- A1 trim pot -> ADC value -> PWM command 0-255 (`map()` then `constrain()`)
- Fixed direction: pin 9 held LOW, trim-pot PWM sent to pin 10 -> H-bridge -> TEC

Safety behavior: both H-bridge inputs are LOW at reset, and a startup latch holds PWM at 0 until the trim pot has been turned to zero once, so the TEC cannot start at a high PWM after a reset.

Example serial line (Serial Monitor only, no plotting):

```text
Temperature (C): 27.73, Time (s): 645.06, PWM: 120, Active PWM pin: 10
```

### Direction test

Performed at low PWM after instructor approval (pin 11, if wired, tied to 5 V).

| Test | Pin 9 | Pin 10 | Observed TEC response |
| --- | --- | --- | --- |
| As written | LOW | PWM | Heating |
| Pins 9/10 control leads swapped at the H-bridge | PWM | LOW | Cooling |

This result is also the mapping used by the Part 6 sketch: HEAT = PWM on pin 10 with pin 9 LOW; COOL = PWM on pin 9 with pin 10 LOW.

Serial record (paste several consecutive lines from each test):

```text
Heating (pin 10 PWM):
TODO

Cooling (leads swapped):
TODO
```

### Why swapping the control leads reverses heating and cooling

Pins 9 and 10 are logic-level inputs to the two half-bridges of the BTS7960. The input that receives PWM switches its half-bridge output (M+ or M-) toward 12 V, while the LOW input holds the other output at ground. Swapping the two control leads therefore swaps which TEC terminal is driven high, reversing the current through the TEC. By the Peltier effect, the direction of the current sets the direction heat is pumped across the TEC, so the plate with the thermistor changes from being heated to being cooled. The TEC power leads (M+/M-) were not moved; only the logic-level control signals were swapped.

## Recommended project structure

- `arduino/tec_manual_fixed_direction/tec_manual_fixed_direction.ino` — first manual trim-pot sketch
- `arduino/tec_manual_hardware_direction/tec_manual_hardware_direction.ino` — manual trim-pot sketch with hardware direction input
- `arduino/tec_python_control/tec_python_control.ino` — serial-command Arduino sketch
- `python/tec_temperature_strip_chart.py` — display-only temperature strip chart
- `python/tec_control_gui.py` — PWM GUI; a user-operated HEAT/COOL control is still needed for bidirectional operation
- `python/tec_serial_check.py` — command-and-read verification helper
- `README.md` — project description, hardware mapping, run instructions, and notes
- `requirements.txt` — Python dependencies

## Hardware mapping

- Thermistor on `A0`
- Trim pot on `A1`
- H-bridge PWM outputs on pins `9` and `10`
- Direction input on pin `11` for the hardware-direction sketch
- Arduino ground connected to H-bridge and oscilloscope ground references

## Example serial measurement line

`Temperature (C): 27.73, Time (s): 645.06, PWM: 120, Heat/Cool: 1`

Meaning:
- `Temperature (C)` = measured thermistor temperature in Celsius
- `Time (s)` = elapsed time in seconds
- `PWM` = duty-cycle command from `0` to `255`
- `Heat/Cool` = `1` for heating, `0` for cooling

## Example serial command

`SET PWM 120 DIR HEAT`

This is the command scheme used by the Python GUI and received by the Arduino control sketch.

## Run order

1. Upload the matching sketch from the `arduino/` directory to the Arduino.
2. Open the serial monitor only to verify measurements or command behavior.
3. Close serial monitor before running the Python GUI.
4. Run the desired Python script:
   - `python python/tec_temperature_strip_chart.py` for display-only plotting with the Part 6 sketch at 115200 baud
   - `python python/tec_control_gui.py` for the current PWM GUI with the Part 6 sketch at 115200 baud
   - `python python/tec_serial_check.py` for command-and-read verification with the Part 6 sketch at 115200 baud

## Checkpoints to record

- pre-power checklist (done — see Part 1 above)
- oscilloscope check of Arduino control pins and H-bridge outputs
- heating serial record
- cooling serial record
- zero-PWM startup check
- paired Arduino/Python integration test
- saved CSV data with units in column headings

## Notes

- Close Arduino Serial Monitor/Plotter before starting Python.
- Do not leave the direction pin floating.
- Always verify the TEC power wiring and thermal cutoff before applying current.
- Use small PWM values at first while confirming heat/cool direction experimentally.
