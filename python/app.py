import os
import stat
import sys
from pathlib import Path

from PySide6 import QtCore


def expose_macos_qt_plugins():
    if sys.platform != "darwin":
        return

    platforms_dir = Path(
        QtCore.QLibraryInfo.path(QtCore.QLibraryInfo.LibraryPath.PluginsPath)
    ) / "platforms"
    for plugin in platforms_dir.glob("*.dylib"):
        flags = plugin.stat().st_flags
        if flags & stat.UF_HIDDEN:
            os.chflags(plugin, flags & ~stat.UF_HIDDEN)


expose_macos_qt_plugins()

from PySide6 import QtWidgets

class MainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Hello World")
        l = QtWidgets.QLabel("My simple app.")
        l.setMargin(10)
        self.setCentralWidget(l)
        self.show()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    app.exec()
