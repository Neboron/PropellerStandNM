#!/usr/bin/env python3
import sys
from PyQt5.QtWidgets import QApplication
from i18n import language_manager
from ui.main_window import MainWindow
from diagnostics.qt_logging import install_runtime_logging
import app_globals

def main():
    app = QApplication(sys.argv)
    language_manager()  # Restore the language before constructing any widgets.
    window = MainWindow()
    restore_logging = install_runtime_logging(window.diagnostics)
    app_globals.window = window  # expose the main window to other modules
    window.show()
    try:
        result = app.exec_()
    finally:
        window.stop_serial_reader()
        restore_logging()
        window.shutdown_diagnostics()
    sys.exit(result)

if __name__ == "__main__":
    main()
