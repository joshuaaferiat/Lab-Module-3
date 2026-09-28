# Module 3: TEC Manual Control and Python GUI

This project follows the [Phys 39 Module 3 assignment](https://sethfraden.github.io/Phys39F26-course/labs/lab-03/). It measures temperature from a thermistor on a thermoelectric cooler (TEC), drives the TEC through an H-bridge, and explores open-loop manual control from Arduino and Python. It does not implement automatic temperature feedback.

## Project Files

| File | Purpose and current status |
| --- | --- |
| `arduino/tec_manual_fixed_direction/tec_manual_fixed_direction.ino` | Part 2 trim-pot control: A0 thermistor, A1 PWM command, pin 10 PWM. Serial rate: 9600 baud. |
| `arduino/tec_manual_hardware_direction/tec_manual_hardware_direction.ino` | Part 3 trim-pot control with a direction switch on pin 11. Serial rate: 9600 baud. |
| `arduino/tec_python_control/tec_python_control.ino` | Part 6 Python-commanded control. Starts at PWM zero, accepts `SET PWM ... DIR ...`, and prints the four-field measurement line at 115200 baud. |
| `python/tec_temperature_strip_chart.py` | Display-only chart for the four-field Part 6 measurement line; writes to `data/module_03/part4_temperature_strip_chart.csv`. |
| `python/archive/part5_tec_control_gui.py` | Part 5 GUI prototype with PWM slider/text entry, measurement readouts, two plots, CSV logging, and serial commands. It has no user-operated HEAT/COOL selector, so bidirectional GUI control remains unfinished. |
| `python/tec_serial_check.py` | Serial command-and-read helper for checking the Part 6 protocol at 115200 baud. |
| `python/archive/part4_extended_serial.py` | Preserved chart variant for the Part 3 extended measurement line. |
| `arduino/legacy/` | Preserved alternate sketches that are not the primary three in this structure. |
| `docs/module_notes/module_03_tec_gui.md` | Part 8 cleanup and C3 checkpoint notes. |
| `docs/figures/module_03/` | Existing `plus.MOV` and `minus.MOV` reference videos. |
| `data/module_03/` | Chart CSV and preserved serial capture. |
| `requirements.txt` | Python dependencies: pyserial, PySide6, and pyqtgraph. |

## Hardware and Direction

- Thermistor divider output: Arduino A0. The sketches average 200 ADC readings before calculating temperature.
- Trim-pot PWM command for the manual sketches: A1.
- Direction switch for the Part 3 hardware-direction sketch: pin 11, connected to 5 V or GND; do not leave it floating.
- H-bridge logic inputs: pins 9 and 10.
- The Part 6 sketch is configured with the experimentally identified mapping: HEAT uses PWM on pin 10 with pin 9 LOW; COOL uses PWM on pin 9 with pin 10 LOW. Confirm direction from the observed temperature response, not from the pin number alone.

The Arduino, H-bridge, and oscilloscope signal reference must share the required ground. Follow the course wiring diagram and safety checklist for the high-current TEC, thermal cutoff, power-supply current limit, and operating heat exchanger. Keep TEC power off while checking logic-level outputs. Never connect an oscilloscope ground clip to an H-bridge output such as M+ or M-; use Arduino GND for probe grounds.

## Serial Interface

`arduino/tec_python_control/tec_python_control.ino` runs at 115200 baud and accepts newline-terminated commands:

```text
SET PWM 120 DIR HEAT
SET PWM 45 DIR COOL
```

PWM is clamped to 0–255. The measurement line is:

```text
Temperature (C): 27.73, Time (s): 645.06, PWM: 120, Heat/Cool: 1
```

`Temperature (C)` is the measured temperature, `Time (s)` is elapsed time, and `PWM` is the commanded value. `Heat/Cool` is 1 for observed heating and 0 for observed cooling; verify that mapping using the physical experiment. The Part 3 sketch emits an extended line with direction-input and active-pin fields at 9600 baud; the archived chart variant matches that format.

## Build and Run

1. Install the Python dependencies in a virtual environment:

	```sh
	python3 -m venv .venv
	source .venv/bin/activate
	python -m pip install -r requirements.txt
	```

2. In the Python script you plan to run, set `PORT` (or `SERIAL_PORT`) to the board's serial device. The checked-in macOS port values are examples, not guaranteed to match another computer.

3. To compile the active Arduino sketch for Uno, select **Arduino: Build active sketch (Uno)** from VS Code's **Terminal > Run Build Task** menu. This task compiles only; it does not upload. The task assumes an Uno (`arduino:avr:uno`). Select the actual board model when uploading.

4. Upload `arduino/tec_python_control/tec_python_control.ino` using an Arduino-aware upload workflow. Start with the board connected and the TEC power off. Before pairing with Python, open Serial Monitor at 115200 baud, choose **Newline**, send a low-PWM test command, and verify pins 9 and 10 with the oscilloscope. The configured pin mapping is HEAT: pin 10 PWM / pin 9 LOW; COOL: pin 9 PWM / pin 10 LOW. Confirm these labels against the observed temperature response. Do not apply TEC power until the wiring and current limit have been checked and the instructor has approved the setup.

5. Close Serial Monitor and Serial Plotter before starting Python; only one program can own the Arduino serial port at a time.

6. Run the matching program:

	- `python python/tec_temperature_strip_chart.py` with the Part 6 sketch at 115200 baud for display-only plotting.
	- `python python/archive/part5_tec_control_gui.py` with the Part 6 sketch at 115200 baud for PWM control and plotting. The GUI still needs a HEAT/COOL input before it can request both directions.
	- `python python/tec_serial_check.py` with the Part 6 sketch at 115200 baud for a command-and-read check. Keep TEC power off or use only the instructor-approved low-power test procedure.

## Data and Verification Status

The Python programs write CSV files with columns `time_s`, `temperature_C`, `pwm`, and `heat_cool` under `data/module_03/`. The checked-in `part4_temperature_strip_chart.csv` currently contains only its header, so it is not an experimental data record. The preserved `part6_pwm0_serial_capture.rtf` shows PWM zero, but does not establish a zero-PWM startup test.

The Part 6 sketch has compiled successfully for the Uno target. A compile does not verify the physical direction mapping, wiring, TEC response, GUI operation, or saved measurements. Record the following after performing the corresponding checks; do not treat code labels as evidence:

- ~~Completed pre-power checklist, wiring/current-limit record, and instructor check.~~ Recorded in `docs/module_notes/module_03_tec_gui.md` (Part 1).
- Oscilloscope observations for pins 9/10 with TEC power off, and M+/M- only after approval and at low PWM.
- Heating and cooling serial records showing that `Heat/Cool` matches observed temperature change.
- Zero-PWM startup, serial-command, Python integration, plot, and CSV checks.
- Any remaining uncertainties and what you verified on the physical apparatus.

## Python Data Flow

| Program | Read and parse | Save and plot | Send |
| --- | --- | --- | --- |
| `python/tec_temperature_strip_chart.py` | `SerialReader.run()` opens `SERIAL_PORT` at `BAUD_RATE` and reads lines; `parse_measurement()` parses the four-field line. | `StripChart.on_line()` stores accepted values and writes `data/module_03/part4_temperature_strip_chart.csv`; `StripChart.update_plot()` draws temperature versus time. | Display-only; it sends no commands. |
| `python/archive/part5_tec_control_gui.py` | `ControlWindow.poll_serial()` reads lines and calls `parse_measurement()`. | `poll_serial()` writes accepted records to `data/module_03/tec_control_data.csv` and updates the temperature and PWM plots. | `ControlWindow.send_command()` writes `SET PWM <value> DIR <direction>` to the serial port. The GUI currently has no user control for selecting direction. |
| `python/tec_serial_check.py` | `main()` reads returned lines and prints them without parsing. | Does not save or plot. | `main()` sends a short sequence of PWM/direction commands for protocol checking. |

- **What I tested myself:** Ran the python code with Arduino to test TEC heating and cooling, adjusting PWM to change the strength of heating and cooling functions. 

## AI Use Note

AI assistance generated the initial Python-commanded Arduino sketch, carried the existing Part 5 GUI source into `python/archive/part5_tec_control_gui.py`, corrected its serial line ending and CSV path, adjusted the chart baud, organized files, and drafted this README. I moved the GUI into the archive during integration. The repository cannot establish which earlier logic changes I personally authored or which parts I can explain without the transcript, so I must complete the personal record above. No hardware test is attributed to AI assistance.
