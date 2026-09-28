#!/usr/bin/env python3
"""Part 7: integrated manual-control verification helper.

This script is a simple serial checker for the paired Part 5 GUI and Part 6
Arduino program. It sends a few low-risk commands and prints the resulting
measurement lines so the operator can verify that PWM and direction are working.
"""

import time
import serial

PORT = "/dev/tty.usbmodem1101"
BAUD = 115200


def main():
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(2.0)

    for pwm, direction in [(0, "HEAT"), (40, "HEAT"), (80, "COOL"), (120, "COOL")]:
        cmd = f"SET PWM {pwm} DIR {direction}\n".encode("utf-8")
        ser.write(cmd)
        time.sleep(0.4)

        for _ in range(10):
            line = ser.readline()
            if not line:
                continue
            print(line.decode("utf-8", errors="replace").strip())

    ser.close()


if __name__ == "__main__":
    main()
