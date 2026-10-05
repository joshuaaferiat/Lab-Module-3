#!/usr/bin/env python3
"""Module 4 TEC calibration GUI with manual direction and PWM control."""

import csv
import math
import os
import queue
import re
import stat
import sys
import threading
from collections import deque
from pathlib import Path

import serial
from PySide6 import QtCore, QtWidgets


def expose_macos_qt_plugins():
    if sys.platform != "darwin":
        return

    plugin_dir = Path(
        QtCore.QLibraryInfo.path(QtCore.QLibraryInfo.LibraryPath.PluginsPath)
    ) / "platforms"
    for path in (plugin_dir, *plugin_dir.glob("*.dylib")):
        flags = path.stat().st_flags
        if flags & stat.UF_HIDDEN:
            os.chflags(path, flags & ~stat.UF_HIDDEN)


expose_macos_qt_plugins()

import pyqtgraph as pg


SERIAL_PORT = "/dev/cu.usbmodem101"
BAUD_RATE = 9600
WINDOW_SECONDS = 60.0
PLOT_UPDATE_MS = 200
CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "module_04" / "tec_calibration.csv"

HEAT_COLOR = "#c43b32"
COOL_COLOR = "#2475a8"

MEASUREMENT_RE = re.compile(
    r"Temperature \(C\):\s*(?P<temperature>-?\d+(?:\.\d+)?|nan)\s*,\s*"
    r"Time \(s\):\s*(?P<time>-?\d+(?:\.\d+)?)\s*,\s*"
    r"PWM:\s*(?P<pwm>\d+)\s*,\s*(?:[^,\r\n]*,\s*)*"
    r"Heat/Cool:\s*(?P<heat_cool>[01])"
)


def parse_measurement(line: str):
    match = MEASUREMENT_RE.search(line)
    if match is None or match.group("temperature").lower() == "nan":
        return None

    temperature = float(match.group("temperature"))
    timestamp = float(match.group("time"))
    if not math.isfinite(temperature) or not math.isfinite(timestamp):
        return None

    return {
        "time_s": timestamp,
        "temperature_C": temperature,
        "pwm": int(match.group("pwm")),
        "heat_cool": int(match.group("heat_cool")),
    }


class SerialWorker(QtCore.QThread):
    line_received = QtCore.Signal(str)
    status_changed = QtCore.Signal(str, bool)

    def __init__(self, port: str, baud: int):
        super().__init__()
        self.port = port
        self.baud = baud
        self.commands = queue.Queue()
        self.stop_requested = threading.Event()

    def send_command(self, pwm: int, direction: str):
        self.commands.put(f"SET PWM {pwm} DIR {direction}\n")

    def stop(self):
        self.send_command(0, "HEAT")
        self.stop_requested.set()
        self.wait(2500)

    def run(self):
        try:
            with serial.Serial(
                self.port,
                self.baud,
                timeout=0.1,
                write_timeout=1.0,
            ) as connection:
                self.stop_requested.wait(2.0)
                if self.stop_requested.is_set():
                    return
                connection.reset_input_buffer()
                self.status_changed.emit(f"Connected: {self.port} at {self.baud} baud", True)

                while True:
                    while True:
                        try:
                            command = self.commands.get_nowait()
                        except queue.Empty:
                            break
                        connection.write(command.encode("ascii"))

                    if self.stop_requested.is_set():
                        break

                    raw_line = connection.readline()
                    if raw_line:
                        self.line_received.emit(raw_line.decode("utf-8", errors="replace").strip())
        except (serial.SerialException, OSError) as exc:
            self.status_changed.emit(f"Serial unavailable: {exc}", False)


class CalibrationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Module 4 TEC Calibration")
        self.resize(1050, 760)
        self.records = deque(maxlen=6000)
        self.csv_file = None
        self.serial_ready = False

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        controls = QtWidgets.QHBoxLayout()
        self.heat_button = QtWidgets.QRadioButton("Heat")
        self.cool_button = QtWidgets.QRadioButton("Cool")
        self.heat_button.setChecked(True)
        self.heat_button.setStyleSheet(f"color: {HEAT_COLOR}; font-weight: 600")
        self.cool_button.setStyleSheet(f"color: {COOL_COLOR}; font-weight: 600")
        direction_group = QtWidgets.QButtonGroup(self)
        direction_group.setExclusive(True)
        direction_group.addButton(self.heat_button)
        direction_group.addButton(self.cool_button)

        controls.addWidget(QtWidgets.QLabel("Direction"))
        controls.addWidget(self.heat_button)
        controls.addWidget(self.cool_button)
        controls.addSpacing(16)
        controls.addWidget(QtWidgets.QLabel("PWM"))

        self.pwm_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.pwm_slider.setRange(0, 255)
        self.pwm_slider.setValue(0)
        self.pwm_slider.setMinimumWidth(220)
        controls.addWidget(self.pwm_slider, 1)

        self.pwm_value = QtWidgets.QLabel("0")
        self.pwm_value.setMinimumWidth(36)
        self.pwm_value.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        controls.addWidget(self.pwm_value)

        self.stop_button = QtWidgets.QPushButton("PWM 0")
        controls.addWidget(self.stop_button)
        layout.addLayout(controls)

        readouts = QtWidgets.QHBoxLayout()
        self.temperature_value = QtWidgets.QLabel("Temperature: -- °C")
        self.time_value = QtWidgets.QLabel("Time: -- s")
        self.measured_pwm_value = QtWidgets.QLabel("Measured PWM: --")
        self.measured_direction = QtWidgets.QLabel("Direction: --")
        readouts.addWidget(self.temperature_value)
        readouts.addWidget(self.time_value)
        readouts.addWidget(self.measured_pwm_value)
        readouts.addWidget(self.measured_direction)
        layout.addLayout(readouts)

        self.temperature_plot = pg.PlotWidget(title="Temperature vs Time")
        self.temperature_plot.setLabel("left", "Temperature", units="°C")
        self.temperature_plot.setLabel("bottom", "Time", units="s")
        self.temperature_plot.showGrid(x=True, y=True, alpha=0.25)
        self.temperature_plot.enableAutoRange(axis="y", enable=True)
        self.temperature_plot.addLegend()
        self.heat_temperature_curve = self.temperature_plot.plot(
            pen=pg.mkPen(HEAT_COLOR, width=2), name="Heating"
        )
        self.cool_temperature_curve = self.temperature_plot.plot(
            pen=pg.mkPen(COOL_COLOR, width=2), name="Cooling"
        )
        layout.addWidget(self.temperature_plot, 3)

        self.pwm_plot = pg.PlotWidget(title="PWM vs Time")
        self.pwm_plot.setLabel("left", "PWM", units="count")
        self.pwm_plot.setLabel("bottom", "Time", units="s")
        self.pwm_plot.setYRange(0, 255, padding=0)
        self.pwm_plot.showGrid(x=True, y=True, alpha=0.25)
        self.pwm_plot.addLegend()
        self.heat_pwm_curve = self.pwm_plot.plot(
            pen=pg.mkPen(HEAT_COLOR, width=2), name="Heating"
        )
        self.cool_pwm_curve = self.pwm_plot.plot(
            pen=pg.mkPen(COOL_COLOR, width=2), name="Cooling"
        )
        layout.addWidget(self.pwm_plot, 2)

        self.status_label = QtWidgets.QLabel(f"Connecting to {SERIAL_PORT}...")
        self.statusBar().addWidget(self.status_label, 1)

        self.command_timer = QtCore.QTimer(self)
        self.command_timer.setSingleShot(True)
        self.command_timer.setInterval(120)
        self.command_timer.timeout.connect(self.send_current_command)

        self.pwm_slider.valueChanged.connect(self.on_pwm_changed)
        self.heat_button.toggled.connect(self.on_direction_changed)
        self.cool_button.toggled.connect(self.on_direction_changed)
        self.stop_button.clicked.connect(self.stop_output)

        self.plot_timer = QtCore.QTimer(self)
        self.plot_timer.timeout.connect(self.update_plots)
        self.plot_timer.start(PLOT_UPDATE_MS)

        self.serial_worker = SerialWorker(SERIAL_PORT, BAUD_RATE)
        self.serial_worker.line_received.connect(self.on_serial_line)
        self.serial_worker.status_changed.connect(self.on_serial_status)
        self.serial_worker.start()
        self.set_controls_enabled(False)

    def set_controls_enabled(self, enabled: bool):
        self.heat_button.setEnabled(enabled)
        self.cool_button.setEnabled(enabled)
        self.pwm_slider.setEnabled(enabled)
        self.stop_button.setEnabled(enabled)

    def current_direction(self) -> str:
        return "HEAT" if self.heat_button.isChecked() else "COOL"

    @QtCore.Slot(int)
    def on_pwm_changed(self, value: int):
        self.pwm_value.setText(str(value))
        self.command_timer.start()

    @QtCore.Slot(bool)
    def on_direction_changed(self, checked: bool):
        if checked:
            self.send_current_command()

    @QtCore.Slot()
    def stop_output(self):
        self.pwm_slider.setValue(0)
        self.send_current_command()

    @QtCore.Slot()
    def send_current_command(self):
        if self.serial_ready and self.serial_worker.isRunning():
            self.serial_worker.send_command(self.pwm_slider.value(), self.current_direction())

    @QtCore.Slot(str, bool)
    def on_serial_status(self, message: str, ready: bool):
        self.serial_ready = ready
        self.status_label.setText(message)
        self.set_controls_enabled(ready)
        if ready:
            self.send_current_command()

    @QtCore.Slot(str)
    def on_serial_line(self, line: str):
        measurement = parse_measurement(line)
        if measurement is None:
            return

        self.records.append(measurement)
        direction = "HEAT" if measurement["heat_cool"] == 1 else "COOL"
        color = HEAT_COLOR if measurement["heat_cool"] == 1 else COOL_COLOR
        self.temperature_value.setText(f"Temperature: {measurement['temperature_C']:.2f} °C")
        self.time_value.setText(f"Time: {measurement['time_s']:.2f} s")
        self.measured_pwm_value.setText(f"Measured PWM: {measurement['pwm']}")
        self.measured_direction.setText(f"Direction: {direction}")
        self.measured_direction.setStyleSheet(f"color: {color}; font-weight: 600")
        self.write_csv_row(measurement)

    def write_csv_row(self, measurement: dict):
        if self.csv_file is None:
            CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
            is_empty = not CSV_PATH.exists() or CSV_PATH.stat().st_size == 0
            self.csv_file = CSV_PATH.open("a", newline="")
            self.csv_writer = csv.writer(self.csv_file)
            if is_empty:
                self.csv_writer.writerow(["time_s", "temperature_C", "pwm", "heat_cool"])

        self.csv_writer.writerow(
            [
                measurement["time_s"],
                measurement["temperature_C"],
                measurement["pwm"],
                measurement["heat_cool"],
            ]
        )
        self.csv_file.flush()

    def update_plots(self):
        if not self.records:
            return

        latest_time = self.records[-1]["time_s"]
        visible = [
            item for item in self.records
            if latest_time - WINDOW_SECONDS <= item["time_s"] <= latest_time
        ]
        times = [item["time_s"] for item in visible]
        heat_temperatures = [
            item["temperature_C"] if item["heat_cool"] == 1 else math.nan
            for item in visible
        ]
        cool_temperatures = [
            item["temperature_C"] if item["heat_cool"] == 0 else math.nan
            for item in visible
        ]
        heat_pwm = [item["pwm"] if item["heat_cool"] == 1 else math.nan for item in visible]
        cool_pwm = [item["pwm"] if item["heat_cool"] == 0 else math.nan for item in visible]

        self.heat_temperature_curve.setData(times, heat_temperatures)
        self.cool_temperature_curve.setData(times, cool_temperatures)
        self.heat_pwm_curve.setData(times, heat_pwm)
        self.cool_pwm_curve.setData(times, cool_pwm)

        start_time = max(0.0, latest_time - WINDOW_SECONDS)
        self.temperature_plot.setXRange(start_time, latest_time, padding=0)
        self.pwm_plot.setXRange(start_time, latest_time, padding=0)

    def closeEvent(self, event):
        self.command_timer.stop()
        self.plot_timer.stop()
        self.serial_worker.stop()
        if self.csv_file is not None:
            self.csv_file.close()
        super().closeEvent(event)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = CalibrationWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()