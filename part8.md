# Module 3 Part 8: Project Cleanup and C3 Checkpoint

This file captures the final organization and verification steps for the TEC manual-control lab.

## Recommended project structure

- `part3.ino` — second manual sketch with hardware direction input
- `part4.py` — display-only temperature strip chart
- `part5.py` — complete GUI with PWM control and serial commands
- `part6.ino` — serial-command Arduino sketch
- `part7.py` — quick verification helper for paired Arduino/Python testing
- `README.md` — project description, hardware mapping, run instructions, and notes

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

1. Upload `part3.ino` or `part6.ino` to the Arduino.
2. Open the serial monitor only to verify measurements or command behavior.
3. Close serial monitor before running the Python GUI.
4. Run the desired Python script:
   - `python part4.py` for display-only plotting
   - `python part5.py` for manual GUI control
   - `python part7.py` for a simple command-and-read verification

## Checkpoints to record

- pre-power checklist
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
