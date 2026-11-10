import sys
from PyQt5.QtCore import pyqtSignal, QTimer, pyqtSlot
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QDoubleSpinBox, QSpinBox, QPushButton, QFrame, QApplication
import serial
import app_globals
from i18n import bind_text
from config import g_const
from workers.serial_reader import SerialReader

class LC_calibration_1(QWidget):
    sendData = pyqtSignal(str)
    updateCalFactor = pyqtSignal(float)
    
    def __init__(self, shared_data):
        super().__init__()
        self.cal_factor = QLabel()
        self.wait_for_cal_factor = False
        self.serialreader = None  # Initialized later
        self.shared_data = shared_data
        self.cal_val_received = False
        self.lc_test = False
        self.thrust_test_value = 0
        self.thr_weight_test_value = 0
        self.torque_test_value = 0
        self.trq_weight_test_value = 0
        self._tare_pending = False
        
        layout4 = QVBoxLayout()
        self.setLayout(layout4)
        
        bind_text(self, 'Stand 1 load cell calibration', property_name="windowTitle")
        
        self.label54 = bind_text(QLabel(), '1. Mount the load cell horizontally on the bracket outside the stand')
        layout4.addWidget(self.label54)
        
        self.label55 = bind_text(QLabel(), '2. Tare the sensor with no load applied')
        layout4.addWidget(self.label55)
        
        self.tare_button = bind_text(QPushButton(self), 'Tare load cells')
        self.tare_button.clicked.connect(self.tare)
        layout4.addWidget(self.tare_button)
        
        self.label58 = bind_text(QLabel(), '3. Enter the load applied to the sensor (grams)')
        layout4.addWidget(self.label58)
        
        self.known_mass = QDoubleSpinBox()
        self.known_mass.setMinimum(0.01)
        self.known_mass.setMaximum(sys.float_info.max)
        self.known_mass.setSingleStep(0.01)
        layout4.addWidget(self.known_mass)
        
        self.label56 = bind_text(QLabel(), '4. Apply the load and select the load cell to calibrate')
        layout4.addWidget(self.label56)
        
        self.cal_thrust_button = bind_text(QPushButton(self), 'Calibrate thrust load cell')
        self.cal_thrust_button.clicked.connect(self.send_cal_thrust)
        layout4.addWidget(self.cal_thrust_button)
        
        self.cal_torque_button = bind_text(QPushButton(self), 'Calibrate torque load cell')
        self.cal_torque_button.clicked.connect(self.send_cal_torque)
        layout4.addWidget(self.cal_torque_button)
        
        self.label60 = bind_text(QLabel(), 'Calibration factor:')
        layout4.addWidget(self.label60)
        
        layout4.addWidget(self.cal_factor)
        
        self.cal_factor.setText('NIL')
        
        self.label59 = bind_text(QLabel(), '5. Write the calibration factor on the load cell')
        layout4.addWidget(self.label59)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)   # optional
        line.setLineWidth(1)                  # optional (or use setFixedHeight)

        layout4.addWidget(line)   
        
        self.label65 = bind_text(QLabel(), 'Torque load cell calibration factor')
        layout4.addWidget(self.label65)
        
        self.torque_cal_val = QDoubleSpinBox()
        self.torque_cal_val.setMinimum(-999999.00)
        self.torque_cal_val.setMaximum(999999.00)
        self.torque_cal_val.setSingleStep(0.01)
        self.torque_cal_val.setValue(self.shared_data.first_trq_cal_val)
        layout4.addWidget(self.torque_cal_val)
        
        self.torque_cal_val_button = bind_text(QPushButton(self), 'Save torque load cell calibration factor')
        self.torque_cal_val_button.clicked.connect(self.send_torque_cal_val)
        layout4.addWidget(self.torque_cal_val_button)
        
        self.label67 = bind_text(QLabel(), 'Thrust load cell calibration factor')
        layout4.addWidget(self.label67)
        
        self.thrust_cal_val = QDoubleSpinBox()
        self.thrust_cal_val.setMinimum(-999999.00)
        self.thrust_cal_val.setMaximum(999999.00)
        self.thrust_cal_val.setSingleStep(0.01)
        self.thrust_cal_val.setValue(self.shared_data.first_thr_cal_val)
        layout4.addWidget(self.thrust_cal_val)
        
        self.thrust_cal_val_button = bind_text(QPushButton(self), 'Save thrust load cell calibration factor')
        self.thrust_cal_val_button.clicked.connect(self.send_thrust_cal_val)
        layout4.addWidget(self.thrust_cal_val_button)
        
        self.label68 = bind_text(QLabel(), 'Torque arm length')
        layout4.addWidget(self.label68)
        
        self.trq_arm_length = QDoubleSpinBox()
        self.trq_arm_length.setMinimum(0.00)
        self.trq_arm_length.setSingleStep(0.01)
        self.trq_arm_length.setValue(self.shared_data.first_trq_arm_length)
        layout4.addWidget(self.trq_arm_length)
        
        self.trq_arm_length_button = bind_text(QPushButton(self), 'Update torque arm length')
        self.trq_arm_length_button.clicked.connect(self.send_trq_arm_length)
        layout4.addWidget(self.trq_arm_length_button)
        
        self.label69 = bind_text(QLabel(), 'Thrust lever ratio (propeller axis / load cell application point)')
        layout4.addWidget(self.label69)
        
        self.thr_arm_length = QDoubleSpinBox()
        self.thr_arm_length.setMinimum(0.00)
        self.thr_arm_length.setSingleStep(0.01)
        self.thr_arm_length.setValue(self.shared_data.first_thr_arm_length)
        layout4.addWidget(self.thr_arm_length)
        
        self.thr_arm_length_button = bind_text(QPushButton(self), 'Update thrust lever ratio')
        self.thr_arm_length_button.clicked.connect(self.send_thr_arm_length)
        layout4.addWidget(self.thr_arm_length_button)
        
        self.lc_test_button = bind_text(QPushButton(self), 'Test load cells')
        self.lc_test_button.setCheckable(True)
        self.lc_test_button.clicked.connect(self.toggle_test)
        layout4.addWidget(self.lc_test_button)
        
        self.label61 = bind_text(QLabel(), 'Corrected thrust load cell reading (N):')
        layout4.addWidget(self.label61)
        
        self.thrust_lc_reading = QLabel()
        layout4.addWidget(self.thrust_lc_reading)
        
        self.labelThr_grams = bind_text(QLabel(), 'Corrected thrust load cell reading (g):')
        layout4.addWidget(self.labelThr_grams)
        
        self.thrust_lc_reading_grams = QLabel()
        layout4.addWidget(self.thrust_lc_reading_grams)
        
        self.label66 = bind_text(QLabel(), 'Raw thrust load cell reading (g):')
        layout4.addWidget(self.label66)
        
        self.thr_weight_lc_reading = QLabel()
        layout4.addWidget(self.thr_weight_lc_reading)
        
        self.label62 = bind_text(QLabel(), 'Torque load cell reading (Nm):')
        layout4.addWidget(self.label62)
        
        self.torque_lc_reading = QLabel()
        layout4.addWidget(self.torque_lc_reading)
        
        self.label63 = bind_text(QLabel(), 'Torque load cell reading (g):')
        layout4.addWidget(self.label63)
        
        self.trq_weight_lc_reading = QLabel()
        layout4.addWidget(self.trq_weight_lc_reading)
        
        self.timer_test = QTimer(self)
        self.timer_test.timeout.connect(self.update_data)
        
        self.timer_cal = QTimer(self)
        self.timer_cal.timeout.connect(self.update_cal_factor_label)
        
    def initialize(self, shared_data):
        self.shared_data = shared_data
        self.serialreader = SerialReader(shared_data)
    
    @pyqtSlot(float)
    def on_cal_factor(self, value: float):
        self.cal_factor.setText(f"{value:.2f}")
        # Reset the pending calibration state.
        self.cal_torque_button.setEnabled(True)
        self.cal_thrust_button.setEnabled(True)
        self.cal_torque_button.setStyleSheet("")
        self.cal_thrust_button.setStyleSheet("")
        self.wait_for_cal_factor = False
        
    def send_cal_torque(self):
        try:
            cal_trq_data = 'calFirstTorque|%.2f' %(self.known_mass.value())
            self.sendData.emit(cal_trq_data)
            self.cal_torque_button.setEnabled(False)
            self.cal_thrust_button.setEnabled(False)
            app_globals.window.cal_val_received = False
            self.cal_torque_button.setStyleSheet("background-color: yellow; color: black;")
        except serial.SerialException as e:
            print(f"Error sending data: {e}")
    
    def send_cal_thrust(self):
        try:
            cal_thrust_data = 'calFirstThrust|%.2f' %(self.known_mass.value())
            self.sendData.emit(cal_thrust_data)
            self.cal_thrust_button.setEnabled(False)
            self.cal_torque_button.setEnabled(False)
            app_globals.window.cal_val_received = False
            self.cal_thrust_button.setStyleSheet("background-color: yellow; color: black;")
        except serial.SerialException as e:
            print(f"Error sending data: {e}")
            
    def update_cal_factor_label(self):
        cal = app_globals.window.cal_value
        print(cal)
        self.cal_factor.setText(f"{cal}")
        if (cal != 0):
            self.cal_torque_button.setEnabled(True)
            self.cal_thrust_button.setEnabled(True)
            self.cal_torque_button.setStyleSheet("background-color: None; color: None;")
            self.cal_thrust_button.setStyleSheet("background-color: None; color: None;")
            self.cal_val_received = False
            self.wait_for_cal_factor = False
            self.timer_cal.stop()
        
    def toggle_test(self):
        if self.lc_test_button.isChecked():
            bind_text(self.lc_test_button, 'Stop test')
            self.test_on()
        else:
            bind_text(self.lc_test_button, 'Test load cells')
            self.test_off()

    def test_on(self):
        app_globals.window.sendData('ON')
        self.timer_test.start(500)
        self.lc_test = True

    def test_off(self):
        app_globals.window.sendData('OFF')
        self.timer_test.stop()
        self.lc_test = False

    def update_data(self):
        try:
            w = app_globals.window

            # MCU corrected outputs (mN and N·mm) -> convert to SI
            thrust_mN  = float(getattr(w, "first_thrust_test_value", 0.0))
            torque_Nmm = float(getattr(w, "first_torque_test_value", 0.0))

            thrust_N   = thrust_mN / 1000.0          # mN -> N
            torque_Nm  = torque_Nmm / 1000.0         # N·mm -> N·m

            # Convert corrected thrust to its equivalent mass in grams.
            thrust_grams_equiv = (thrust_N / g_const) * 1000.0 * self.shared_data.first_thr_arm_length

            thr_raw_g = float(getattr(w, "first_thr_weight_test_value", 0.0))
            trq_raw_g = float(getattr(w, "first_trq_weight_test_value", 0.0))

            self.thrust_lc_reading.setText(f"{thrust_N:.2f}")
            self.thrust_lc_reading_grams.setText(f"{thr_raw_g:.2f}")
            self.thr_weight_lc_reading.setText(f"{thrust_grams_equiv:.2f}")

            self.torque_lc_reading.setText(f"{torque_Nm:.3f}")
            self.trq_weight_lc_reading.setText(f"{trq_raw_g:.2f}")
        except Exception as e:
            print("update_data error:", e)

    def tare(self):
        # send the command
        self.sendData.emit('tare')

        # mark as pending and show yellow
        self._tare_pending = True
        btn = self.tare_button
        btn.setEnabled(False)
        bind_text(btn, 'Taring…')
        btn.setStyleSheet("QPushButton { background-color: yellow; color: black; }")
        # force a paint right now
        QApplication.processEvents()
        
        QTimer.singleShot(8000, self._finish_tare_if_stuck)

    def _finish_tare_if_stuck(self):
        if self._tare_pending:
            self.on_tare_done()

    @pyqtSlot()
    def on_tare_done(self):
        self._tare_pending = False

        btn = self.tare_button
        # clear any old styling first
        btn.setStyleSheet("")
        btn.setEnabled(True)
        bind_text(btn, 'Tare load cells ✓')
        btn.setStyleSheet("QPushButton { background-color: green; color: white; }")

        QTimer.singleShot(1200, lambda: (btn.setStyleSheet(""), bind_text(btn, 'Tare load cells')))

        # hard repaint in case something queued tries to override
        btn.style().unpolish(btn)
        btn.style().polish(btn)
        btn.update()
        QApplication.processEvents()
            
    def send_torque_cal_val(self):
        torque_cal_val_data = 'setFirstTrqCalVal|%.2f' %(self.torque_cal_val.value())
        self.sendData.emit(torque_cal_val_data)
        self.shared_data.first_trq_cal_val = float(self.torque_cal_val.value())
        
    def send_thrust_cal_val(self):
        thrust_cal_val_data = 'setFirstThrCalVal|%.2f' %(self.thrust_cal_val.value())
        self.sendData.emit(thrust_cal_val_data)
        self.shared_data.first_thr_cal_val = float(self.thrust_cal_val.value())
        
    def send_trq_arm_length(self):
        trq_arm_length_data = 'setFirstTrqArmLength|%.2f' %(self.trq_arm_length.value())
        self.sendData.emit(trq_arm_length_data)
        
    def send_thr_arm_length(self):
        thr_arm_length_data = 'setFirstThrArmLength|%.2f' %(self.thr_arm_length.value())
        self.sendData.emit(thr_arm_length_data)
        
    def closeEvent(self, event):
        """Make sure MCU is switched OFF when calibration window closes."""
        try:
            app_globals.window.sendData('OFF')   # send OFF to MCU
        except Exception:
            pass
        try:
            self.timer_test.stop()
        except Exception:
            pass
        self.lc_test = False
        try:
            if self.lc_test_button.isChecked():
                self.lc_test_button.setChecked(False)
            bind_text(self.lc_test_button, 'Test load cells')
        except Exception:
            pass
        event.accept()  # let the window close
