#!/usr/bin/env python3
"""Part 4: display-only temperature strip chart for the TEC lab.

This script opens the Arduino serial port, parses the measurement line,
prints only the useful values, stores a CSV of the accepted data, and updates
an on-screen temperature plot.
"""

import csv
import re
import sys
from collections import deque

import serial
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from pyqtgraph import PlotWidget

PORT = "/dev/tty.usbmodem1101"  # Change for your machine, e.g. COM3 on Windows
# These settings control the serial connection, display, and saved data.
BAUD = 9600
WINDOW_SECONDS = 60.0
PLOT_INTERVAL_MS = 100
TEMP_Y_MIN = 0.0
TEMP_Y_MAX = 40.0
OUTPUT_FILE = "part4_temperature_data.csv"

# This matches the measurement line printed by m3_p3.ino.
MEASUREMENT_PATTERN = re.compile(
    r"Temperature \(C\):\s*([-+]?\d*\.?\d+)"
    r"\s*,\s*Time \(s\):\s*([-+]?\d*\.?\d+)"
    r"\s*,\s*PWM:\s*(\d+)"
    r"\s*,\s*Direction input:\s*[01]"
    r"\s*,\s*Active PWM pin:\s*\d+"
    r"\s*,\s*Heat/Cool:\s*([01])"
)


def parse_measurement(line: str):
    match = MEASUREMENT_PATTERN.search(line.strip())
    if not match:
        return None

    temperature_c, time_s, pwm_value, heat_cool = match.groups()
    return {
        "time_s": float(time_s),
        "temperature_C": float(temperature_c),
        "pwm": int(pwm_value),
        "heat_cool": int(heat_cool),
    }


class TemperatureStripChartApp:
    def __init__(self):
        # Create the application window and temperature plot.
        self.app = QApplication(sys.argv)
        self.plot_widget = PlotWidget(title="Temperature vs Time")
        self.plot_widget.setYRange(TEMP_Y_MIN, TEMP_Y_MAX)
        self.plot_widget.setXRange(0, WINDOW_SECONDS)

        # Keep the recent data needed for the rolling chart.
        self.time_history = deque()
        self.temperature_history = deque()

        # Open the Arduino connection and prepare the CSV file.
        self.serial_port = serial.Serial(PORT, BAUD, timeout=0.1)

        self.csv_file = open(OUTPUT_FILE, "w", newline="")
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(["time_s", "temperature_C", "pwm", "heat_cool"])

        # Read serial data regularly without blocking the user interface.
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(PLOT_INTERVAL_MS)

    def update(self):
        while self.serial_port.in_waiting:
            raw_line = self.serial_port.readline().decode("utf-8", errors="replace")
            if not raw_line:
                continue
            parsed = parse_measurement(raw_line)
            if parsed is None:
                continue

            print(
                f"Temperature (C): {parsed['temperature_C']:.2f}, "
                f"Time (s): {parsed['time_s']:.2f}, "
                f"PWM: {parsed['pwm']}, "
                f"Heat/Cool: {parsed['heat_cool']}"
            )

            self.time_history.append(parsed["time_s"])
            self.temperature_history.append(parsed["temperature_C"])
            self.csv_writer.writerow(
                [
                    parsed["time_s"],
                    parsed["temperature_C"],
                    parsed["pwm"],
                    parsed["heat_cool"],
                ]
            )
            self.csv_file.flush()

            # Remove samples older than the selected rolling time window.
            oldest_allowed = parsed["time_s"] - WINDOW_SECONDS
            while self.time_history and self.time_history[0] < oldest_allowed:
                self.time_history.popleft()
                self.temperature_history.popleft()

        if len(self.time_history) >= 2:
            newest_time = self.time_history[-1]
            oldest_time = max(0.0, newest_time - WINDOW_SECONDS)
            self.plot_widget.setXRange(oldest_time, newest_time)
            self.plot_widget.plot(list(self.time_history), list(self.temperature_history), clear=True)

    def run(self):
        self.plot_widget.show()
        self.app.exec()


if __name__ == "__main__":
    try:
        app = TemperatureStripChartApp()
        app.run()
    finally:
        try:
            app.serial_port.close()
        except Exception:
            pass
        try:
            app.csv_file.close()
        except Exception:
            pass
