# Phys 39 Module 3 - Part 4
# Display-only temperature strip chart
#
# Reads the standard Arduino measurement line:
#   Temperature (C): 27.73, Time (s): 645.06, PWM: 120, Heat/Cool: 1
#
# Plots ONLY temperature vs time.
# Prints ONLY the four extracted fields to the VS Code terminal.
# Saves CSV with columns: time_s, temperature_C, pwm, heat_cool

import sys
import re
from collections import deque
from pathlib import Path

import serials
from PySide6 import QtCore, QtWidgets
import pyqtgraph as pg


# ------------------------------------------------------------------
# CONFIGURATION  (edit these near the top)
# ------------------------------------------------------------------
SERIAL_PORT = "COM5"                # Windows example. macOS: /dev/cu.usbmodemXXXX
                                    # Linux: /dev/ttyACM0 or /dev/ttyUSB0
BAUD_RATE = 9600

WINDOW_SECONDS = 60.0               # visible strip-chart window duration
PLOT_UPDATE_MS = 100                # plot update interval (ms)

TEMP_Y_MIN = 15.0                   # temperature-axis lower limit (C)
TEMP_Y_MAX = 45.0                   # temperature-axis upper limit (C)

CSV_PATH = Path("data/module_03/part4_temperature_strip_chart.csv")
# ------------------------------------------------------------------


# ------------------------------------------------------------------
# READ SERIAL DATA: parse one measurement line
# ------------------------------------------------------------------
MEAS_RE = re.compile(
    r"Temperature \(C\):\s*(?P<temp>-?\d+(?:\.\d+)?|nan)\s*,\s*"
    r"Time \(s\):\s*(?P<time>-?\d+(?:\.\d+)?)\s*,\s*"
    r"PWM:\s*(?P<pwm>\d+)\s*,\s*"
    r"Heat/Cool:\s*(?P<hc>[01])"
)


def parse_measurement(line: str):
    """Return dict of fields, or None if the line is not a valid measurement."""
    m = MEAS_RE.search(line)
    if not m:
        return None
    if m.group("temp") == "nan":
        return None
    return {
        "time_s": float(m.group("time")),
        "temperature_C": float(m.group("temp")),
        "pwm": int(m.group("pwm")),
        "heat_cool": int(m.group("hc")),
    }


# ------------------------------------------------------------------
# READ SERIAL DATA: background thread
# ------------------------------------------------------------------
class SerialReader(QtCore.QThread):
    line_received = QtCore.Signal(str)
    error = QtCore.Signal(str)

    def __init__(self, port: str, baud: int):
        super().__init__()
        self.port = port
        self.baud = baud
        self._stop = False

    def run(self):
        try:
            with serial.Serial(self.port, self.baud, timeout=0.5) as ser:
                while not self._stop:
                    raw = ser.readline()
                    if not raw:
                        continue
                    try:
                        line = raw.decode("utf-8", errors="replace").strip()
                    except Exception:
                        continue
                    if line:
                        self.line_received.emit(line)
        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        self._stop = True
        self.wait(1000)


# ------------------------------------------------------------------
# GUI + PLOT
# ------------------------------------------------------------------
class StripChart(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Part 4 - Temperature Strip Chart")

        # STORE RECENT DATA
        self.data = deque()   # each entry: (time_s, temperature_C, pwm, heat_cool)

        # SAVE THE CSV FILE
        self.csv_path = CSV_PATH
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self.csv_file = open(self.csv_path, "w", newline="")
        self.csv_file.write("time_s,temperature_C,pwm,heat_cool\n")
        self.csv_file.flush()

        # UPDATE THE PLOT: widget setup
        self.plot = pg.PlotWidget()
        self.plot.setLabel("bottom", "Time (s)")
        self.plot.setLabel("left", "Temperature (C)")
        self.plot.setYRange(TEMP_Y_MIN, TEMP_Y_MAX)
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.curve = self.plot.plot(pen=pg.mkPen(width=2))
        self.setCentralWidget(self.plot)
        self.resize(900, 500)

        # READ SERIAL DATA: start reader thread
        self.reader = SerialReader(SERIAL_PORT, BAUD_RATE)
        self.reader.line_received.connect(self.on_line)
        self.reader.error.connect(self.on_serial_error)
        self.reader.start()

        # UPDATE THE PLOT: timer
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(PLOT_UPDATE_MS)

    # -------------- one line received --------------
    @QtCore.Slot(str)
    def on_line(self, line: str):
        parsed = parse_measurement(line)
        if parsed is None:
            return

        t = parsed["time_s"]
        T = parsed["temperature_C"]
        pwm = parsed["pwm"]
        hc = parsed["heat_cool"]

        # PRINT EXTRACTED FIELDS ONLY (no raw line echoed)
        print(f"t={t:8.2f} s  T={T:6.2f} C  PWM={pwm:3d}  H/C={hc}")

        # STORE RECENT DATA
        self.data.append((t, T, pwm, hc))

        # SAVE THE CSV FILE
        self.csv_file.write(f"{t:.2f},{T:.3f},{pwm},{hc}\n")
        self.csv_file.flush()

    @QtCore.Slot(str)
    def on_serial_error(self, msg: str):
        print(f"[serial error] {msg}")

    # -------------- update plot --------------
    def update_plot(self):
        if not self.data:
            return
        xs = [d[0] for d in self.data]
        ys = [d[1] for d in self.data]
        self.curve.setData(xs, ys)
        t_latest = xs[-1]
        self.plot.setXRange(max(0.0, t_latest - WINDOW_SECONDS), t_latest, padding=0)

    # -------------- clean shutdown --------------
    def closeEvent(self, event):
        self.timer.stop()
        self.reader.stop()
        if self.csv_file is not None:
            self.csv_file.close()
            self.csv_file = None
        super().closeEvent(event)


# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------
def main():
    app = QtWidgets.QApplication(sys.argv)
    w = StripChart()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
