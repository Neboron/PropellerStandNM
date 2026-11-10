import sys
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QDoubleSpinBox, QSpinBox,
    QPushButton, QMessageBox, QHBoxLayout
)
import serial
from i18n import bind_text


class AoA_AoSS(QWidget):
    sendData = pyqtSignal(str)

    def __init__(self, shared_data):
        super().__init__()
        self.shared_data = shared_data

        # Track AoSS enable/disable state to warn on close
        self._aoss_disabled = False

        layout = QVBoxLayout()
        self.setLayout(layout)
        bind_text(self, 'AoA and AoSS axis parameters', property_name="windowTitle")

        # ---------------- AoA ----------------
        self.label50 = bind_text(QLabel(), 'AoA axis trim (degrees)')
        layout.addWidget(self.label50)

        self.aoa_trim = QDoubleSpinBox()
        self.aoa_trim.setMinimum(-150)
        self.aoa_trim.setMaximum(150)
        self.aoa_trim.setSingleStep(0.1)
        self.aoa_trim.setValue(float(getattr(self.shared_data, "aoa_trim", 0.0)))
        layout.addWidget(self.aoa_trim)

        self.aoa_trim_button = bind_text(QPushButton(self), 'Apply AoA trim')
        self.aoa_trim_button.clicked.connect(self.send_aoa_trim)
        layout.addWidget(self.aoa_trim_button)

        self.label_read_aoa_title = bind_text(QLabel(), 'AoA angle (deg)')
        layout.addWidget(self.label_read_aoa_title)

        self.label_read_aoa_value = QLabel("—")
        self.label_read_aoa_value.setStyleSheet("border: 1px solid black; padding: 4px;")
        layout.addWidget(self.label_read_aoa_value)

        self.read_aoa_button = bind_text(QPushButton(self), 'Read angle')
        self.read_aoa_button.clicked.connect(self.send_read_aoa)
        layout.addWidget(self.read_aoa_button)

        self.label51 = bind_text(QLabel(), 'Maximum AoA travel from zero (degrees)')
        layout.addWidget(self.label51)

        self.aoa_limit = QSpinBox()
        self.aoa_limit.setMinimum(1)
        self.aoa_limit.setMaximum(90)
        self.aoa_limit.setSingleStep(1)
        self.aoa_limit.setValue(int(getattr(self.shared_data, "aoa_limit", 30)))
        layout.addWidget(self.aoa_limit)

        self.aoa_limit_button = bind_text(QPushButton(self), 'Apply AoA limit')
        self.aoa_limit_button.clicked.connect(self.send_aoa_limit)
        layout.addWidget(self.aoa_limit_button)

        # ---------------- AoSS ----------------
        layout.addWidget(QLabel(""))

        self.aoss_title = bind_text(QLabel(), 'AoSS axis calibration and parameters')
        self.aoss_title.setStyleSheet("font-weight: 600;")
        layout.addWidget(self.aoss_title)

        self.aoss_hint = bind_text(
            QLabel(),
            "Procedure:\n"
            "1) Adjust AoSSRatio (if needed)\n"
            "2) Set AoSS axis limits (min..max)\n"
            "3) Before calibration: disableAoSS\n"
            "4) Move the tube to physical zero: moveAoSSTubeAbs|\n"
            "5) Check position: readAoSS\n"
            "6) Save zero: zeroAoSS\n"
            "7) Finish with: enableAoSS"
        )
        self.aoss_hint.setStyleSheet("color: #555;")
        layout.addWidget(self.aoss_hint)

        # Ratio
        self.label_ratio = bind_text(QLabel(), 'AoSSRatio')
        layout.addWidget(self.label_ratio)

        self.aoss_ratio = QDoubleSpinBox()
        self.aoss_ratio.setMinimum(0.01)
        self.aoss_ratio.setMaximum(1000.0)
        self.aoss_ratio.setSingleStep(0.01)
        self.aoss_ratio.setDecimals(4)
        self.aoss_ratio.setValue(float(getattr(self.shared_data, "aoss_ratio", 13.3)))
        layout.addWidget(self.aoss_ratio)

        self.aoss_ratio_button = bind_text(QPushButton(self), 'Apply AoSSRatio')
        self.aoss_ratio_button.clicked.connect(self.send_aoss_ratio)
        layout.addWidget(self.aoss_ratio_button)

        # Limits
        self.label_limits = bind_text(QLabel(), 'AoSS axis limits (deg) – min down to -45, max up to 0')
        layout.addWidget(self.label_limits)

        limits_row = QHBoxLayout()
        self.aoss_min_limit = QDoubleSpinBox()
        self.aoss_min_limit.setMinimum(-33.0)
        self.aoss_min_limit.setMaximum(0.0)
        self.aoss_min_limit.setSingleStep(0.5)
        self.aoss_min_limit.setDecimals(1)
        self.aoss_min_limit.setValue(float(getattr(self.shared_data, "aoss_min_limit_deg", -32.0)))

        self.aoss_max_limit = QDoubleSpinBox()
        self.aoss_max_limit.setMinimum(-33.0)
        self.aoss_max_limit.setMaximum(0.0)
        self.aoss_max_limit.setSingleStep(0.5)
        self.aoss_max_limit.setDecimals(1)
        self.aoss_max_limit.setValue(float(getattr(self.shared_data, "aoss_max_limit_deg", 0.0)))

        limits_row.addWidget(bind_text(QLabel(), 'min'))
        limits_row.addWidget(self.aoss_min_limit)
        limits_row.addWidget(bind_text(QLabel(), 'max'))
        limits_row.addWidget(self.aoss_max_limit)
        layout.addLayout(limits_row)

        self.aoss_limits_button = bind_text(QPushButton(self), 'Apply AoSS limits')
        self.aoss_limits_button.clicked.connect(self.send_aoss_limits)
        layout.addWidget(self.aoss_limits_button)

        # Calibration controls
        layout.addWidget(QLabel(""))

        self.aoss_state_label = bind_text(QLabel(), 'AoSS status: —')
        self.aoss_state_label.setStyleSheet("border: 1px solid black; padding: 4px;")
        layout.addWidget(self.aoss_state_label)

        self.disable_aoss_button = bind_text(QPushButton(self), 'Disable AoSS axis')
        self.disable_aoss_button.clicked.connect(self.send_disable_aoss)
        layout.addWidget(self.disable_aoss_button)

        self.move_label = bind_text(QLabel(), 'Move AoSS tube (absolute, deg)')
        layout.addWidget(self.move_label)

        self.move_abs = QDoubleSpinBox()
        self.move_abs.setMinimum(-32.0)
        self.move_abs.setMaximum(0.0)
        self.move_abs.setSingleStep(0.1)
        self.move_abs.setDecimals(2)
        self.move_abs.setValue(0.0)
        layout.addWidget(self.move_abs)

        self.move_abs_button = bind_text(QPushButton(self), 'Move tube: moveAoSSTubeAbs|')
        self.move_abs_button.clicked.connect(self.send_move_aoss_tube_abs)
        layout.addWidget(self.move_abs_button)

        self.label_read_aoss_title = bind_text(QLabel(), 'Read AoSS position (tube deg)')
        layout.addWidget(self.label_read_aoss_title)

        self.label_read_aoss_value = QLabel("—")
        self.label_read_aoss_value.setStyleSheet("border: 1px solid black; padding: 4px;")
        layout.addWidget(self.label_read_aoss_value)

        self.read_aoss_button = bind_text(QPushButton(self), 'Read AoSS position: readAoSS')
        self.read_aoss_button.clicked.connect(self.send_read_aoss)
        layout.addWidget(self.read_aoss_button)

        self.zero_aoss_button = bind_text(QPushButton(self), 'Set current position to zero: zeroAoSS')
        self.zero_aoss_button.clicked.connect(self.send_zero_aoss)
        layout.addWidget(self.zero_aoss_button)

        self.enable_aoss_button = bind_text(QPushButton(self), 'Enable AoSS')
        self.enable_aoss_button.clicked.connect(self.send_enable_aoss)
        layout.addWidget(self.enable_aoss_button)

        # --- change highlighting ---
        self.aoa_trim.valueChanged.connect(lambda: self._mark_dirty(self.aoa_trim_button))
        self.aoa_limit.valueChanged.connect(lambda: self._mark_dirty(self.aoa_limit_button))

        self.aoss_ratio.valueChanged.connect(lambda: self._mark_dirty(self.aoss_ratio_button))
        self.aoss_min_limit.valueChanged.connect(lambda: self._mark_dirty(self.aoss_limits_button))
        self.aoss_max_limit.valueChanged.connect(lambda: self._mark_dirty(self.aoss_limits_button))

    def _mark_dirty(self, btn: QPushButton):
        try:
            btn.setStyleSheet("background-color: orange; color: black;")
        except Exception:
            pass

    # ---------------- AoA senders ----------------
    def send_aoa_trim(self):
        try:
            self.shared_data.aoa_trim = self.aoa_trim.value()
            self.sendData.emit(f"trimAoA|{self.shared_data.aoa_trim:.6f}")
            self.aoa_trim_button.setStyleSheet("background-color: None; color: None;")
        except serial.SerialException as e:
            print(f"Error sending data: {e}")

    def send_aoa_limit(self):
        try:
            self.shared_data.aoa_limit = int(self.aoa_limit.value())
            self.sendData.emit(f"AoAlim|{self.shared_data.aoa_limit:d}")
            self.aoa_limit_button.setStyleSheet("background-color: None; color: None;")
        except serial.SerialException as e:
            print(f"Error sending data: {e}")

    def send_read_aoa(self):
        try:
            self.sendData.emit("readAoA")
        except serial.SerialException as e:
            print(f"Error sending data: {e}")

    def set_read_aoa_value(self, val: str):
        try:
            self.label_read_aoa_value.setText(str(val))
        except Exception:
            pass

    # ---------------- AoSS senders (NEW) ----------------
    def send_aoss_ratio(self):
        try:
            val = float(self.aoss_ratio.value())
            try:
                self.shared_data.aoss_ratio = val
            except Exception:
                pass
            self.sendData.emit(f"setAoSSRatio|{val:.6f}")
            self.aoss_ratio_button.setStyleSheet("background-color: None; color: None;")
        except serial.SerialException as e:
            print(f"Error sending data: {e}")

    def send_aoss_limits(self):
        try:
            mn = float(self.aoss_min_limit.value())
            mx = float(self.aoss_max_limit.value())
            # Ensure order (MCU also enforces, but keep UI sane)
            if mn > mx:
                mn, mx = mx, mn
                self.aoss_min_limit.setValue(mn)
                self.aoss_max_limit.setValue(mx)

            try:
                self.shared_data.aoss_min_limit_deg = mn
                self.shared_data.aoss_max_limit_deg = mx
            except Exception:
                pass

            # MCU expects: setAoSSLimits|min|max
            self.sendData.emit(f"setAoSSLimits|{mn:.2f}|{mx:.2f}")
            self.aoss_limits_button.setStyleSheet("background-color: None; color: None;")
        except serial.SerialException as e:
            print(f"Error sending data: {e}")

    def send_disable_aoss(self):
        try:
            self.sendData.emit("disableAoSS")
            self._aoss_disabled = True
            bind_text(self.aoss_state_label, 'AoSS status: disabled (calibration)')
            self.aoss_state_label.setStyleSheet("border: 1px solid black; padding: 4px; background-color: orange;")
        except serial.SerialException as e:
            print(f"Error sending data: {e}")

    def send_enable_aoss(self):
        try:
            self.sendData.emit("enableAoSS")
            self._aoss_disabled = False
            bind_text(self.aoss_state_label, 'AoSS status: enabled')
            self.aoss_state_label.setStyleSheet("border: 1px solid black; padding: 4px; background-color: None;")
        except serial.SerialException as e:
            print(f"Error sending data: {e}")

    def send_move_aoss_tube_abs(self):
        try:
            tube = float(self.move_abs.value())
            self.sendData.emit(f"moveAoSSTubeAbs|{tube:.2f}")
        except serial.SerialException as e:
            print(f"Error sending data: {e}")

    def send_read_aoss(self):
        try:
            self.sendData.emit("readAoSS")
        except serial.SerialException as e:
            print(f"Error sending data: {e}")

    def set_read_aoss_value(self, tube_deg: str, servo_deg: str = None, turn: str = None, pos: str = None):
        """Update the widget label with parsed AoSS readback (tube deg is primary)."""
        try:
            txt = str(tube_deg)
            extras = []
            if servo_deg is not None:
                extras.append(f"servo={servo_deg}")
            if turn is not None:
                extras.append(f"turn={turn}")
            if pos is not None:
                extras.append(f"pos={pos}")
            if extras:
                txt = f"{txt}  ({', '.join(extras)})"
            self.label_read_aoss_value.setText(txt)
        except Exception:
            pass

    def send_zero_aoss(self):
        try:
            self.sendData.emit("zeroAoSS")
        except serial.SerialException as e:
            print(f"Error sending data: {e}")

    # ---------------- close prompt ----------------
    def closeEvent(self, event):
        # If user disabled AoSS for calibration but didn't enable it back, warn/prompt.
        if getattr(self, "_aoss_disabled", False):
            mb = QMessageBox(self)
            mb.setIcon(QMessageBox.Warning)
            bind_text(mb, 'AoSS axis is disabled', property_name="windowTitle")
            bind_text(mb, 'The AoSS axis is currently disabled.\nEnable it before closing?')
            mb.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            bind_text(mb.button(QMessageBox.Yes), "Yes")
            bind_text(mb.button(QMessageBox.No), "No")
            bind_text(mb.button(QMessageBox.Cancel), "Cancel")
            mb.setDefaultButton(QMessageBox.Yes)
            ret = mb.exec_()

            if ret == QMessageBox.Yes:
                try:
                    self.send_enable_aoss()
                except Exception:
                    pass
                event.accept()
                return
            if ret == QMessageBox.Cancel:
                event.ignore()
                return
        event.accept()
