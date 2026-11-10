import sys
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QDoubleSpinBox, QSpinBox, QPushButton, QCheckBox
import app_globals
from i18n import bind_text

class SetParameters(QWidget):
    sendData = pyqtSignal(str)

    def __init__(self, shared_data):
        super().__init__()
        self.shared_data = shared_data
        self._pending_values = None
        layout1 = QVBoxLayout(); self.setLayout(layout1)
        bind_text(self, 'Sensor parameters', property_name="windowTitle")
        
        self.label1 = bind_text(QLabel(), 'Air density (kg/m3)')
        layout1.addWidget(self.label1)
        
        self.rho = QDoubleSpinBox()
        self.rho.setMinimum(0)
        self.rho.setDecimals(3)
        self.rho.setSingleStep(0.001)
        self.rho.setValue(self.shared_data.rho)
        layout1.addWidget(self.rho)
        
        self.label2 = bind_text(QLabel(), 'Kinematic viscosity (m2/s)')
        layout1.addWidget(self.label2)
        
        self.kin_visc = QDoubleSpinBox()
        self.kin_visc.setMinimum(0)
        self.kin_visc.setDecimals(2)
        self.kin_visc.setSingleStep(0.01)
        self.kin_visc.setValue(self.shared_data.kin_visc)
        layout1.addWidget(self.kin_visc)
        
        self.tandem = bind_text(QCheckBox(self), 'Tandem rotors')
        self.tandem.setChecked(self.shared_data.no_of_props == 2)
        self.tandem.toggled.connect(self.set_tandem_flag)
        layout1.addWidget(self.tandem)
        
        self.label_probe_offset = bind_text(QLabel(), 'Pitot probe offset from center (mm)')
        layout1.addWidget(self.label_probe_offset)

        self.probe_offset = QDoubleSpinBox()
        self.probe_offset.setMinimum(0.0)   # Nonnegative probe offset in mm
        self.probe_offset.setMaximum(50.0)
        self.probe_offset.setSingleStep(0.1)
        self.probe_offset.setDecimals(2)
        self.probe_offset.setValue(getattr(self.shared_data, "probe_offset", 0.0))
        self.probe_offset.setEnabled(self.tandem.isChecked())
        layout1.addWidget(self.probe_offset)


        
        self.label3 = bind_text(QLabel(), 'Stand 1 torque arm length (mm)')
        layout1.addWidget(self.label3)
        
        self.first_trq_arm_length = QDoubleSpinBox()
        self.first_trq_arm_length.setMinimum(0.00)
        self.first_trq_arm_length.setSingleStep(0.01)
        self.first_trq_arm_length.setValue(self.shared_data.first_trq_arm_length)
        layout1.addWidget(self.first_trq_arm_length)
        
        self.label4 = bind_text(QLabel(), 'Stand 1 torque load cell calibration factor')
        layout1.addWidget(self.label4)
        
        self.first_trq_lc_factor = QDoubleSpinBox()
        self.first_trq_lc_factor.setMinimum(-sys.float_info.max)
        self.first_trq_lc_factor.setMaximum(sys.float_info.max)
        self.first_trq_lc_factor.setSingleStep(0.01)
        self.first_trq_lc_factor.setValue(self.shared_data.first_trq_cal_val)
        layout1.addWidget(self.first_trq_lc_factor)
        
        self.label5 = bind_text(QLabel(), 'Stand 1 thrust lever ratio (axis / load point)')
        layout1.addWidget(self.label5)
        
        self.first_thr_arm_length = QDoubleSpinBox()
        self.first_thr_arm_length.setMinimum(-sys.float_info.max)
        self.first_thr_arm_length.setMaximum(sys.float_info.max)
        self.first_thr_arm_length.setSingleStep(0.01)
        self.first_thr_arm_length.setValue(self.shared_data.first_thr_arm_length)
        layout1.addWidget(self.first_thr_arm_length)
        
        self.label6 = bind_text(QLabel(), 'Stand 1 thrust load cell calibration factor')
        layout1.addWidget(self.label6)
        
        self.first_thr_lc_factor = QDoubleSpinBox()
        self.first_thr_lc_factor.setMinimum(-sys.float_info.max)
        self.first_thr_lc_factor.setMaximum(sys.float_info.max)
        self.first_thr_lc_factor.setSingleStep(0.01)
        self.first_thr_lc_factor.setValue(self.shared_data.first_thr_cal_val)
        layout1.addWidget(self.first_thr_lc_factor)
        
        self.label7 = bind_text(QLabel(), 'Stand 2 torque arm length (mm)')
        layout1.addWidget(self.label7)
        
        self.second_trq_arm_length = QDoubleSpinBox()
        self.second_trq_arm_length.setMinimum(0.00)
        self.second_trq_arm_length.setSingleStep(0.01)
        self.second_trq_arm_length.setValue(self.shared_data.second_trq_arm_length)
        layout1.addWidget(self.second_trq_arm_length)
        
        self.label8 = bind_text(QLabel(), 'Stand 2 torque load cell calibration factor')
        layout1.addWidget(self.label8)
        
        self.second_trq_lc_factor = QDoubleSpinBox()
        self.second_trq_lc_factor.setMinimum(-sys.float_info.max)
        self.second_trq_lc_factor.setMaximum(sys.float_info.max)
        self.second_trq_lc_factor.setSingleStep(0.01)
        self.second_trq_lc_factor.setValue(self.shared_data.second_trq_cal_val)
        layout1.addWidget(self.second_trq_lc_factor)
        
        self.label9 = bind_text(QLabel(), 'Stand 2 thrust lever ratio (axis / load point)')
        layout1.addWidget(self.label9)
        
        self.second_thr_arm_length = QDoubleSpinBox()
        self.second_thr_arm_length.setMinimum(-sys.float_info.max)
        self.second_thr_arm_length.setMaximum(sys.float_info.max)
        self.second_thr_arm_length.setSingleStep(0.01)
        self.second_thr_arm_length.setValue(self.shared_data.second_thr_arm_length)
        layout1.addWidget(self.second_thr_arm_length)
        
        self.label10 = bind_text(QLabel(), 'Stand 2 thrust load cell calibration factor')
        layout1.addWidget(self.label10)
        
        self.second_thr_lc_factor = QDoubleSpinBox()
        self.second_thr_lc_factor.setMinimum(-sys.float_info.max)
        self.second_thr_lc_factor.setMaximum(sys.float_info.max)
        self.second_thr_lc_factor.setSingleStep(0.01)
        self.second_thr_lc_factor.setValue(self.shared_data.second_thr_cal_val)
        layout1.addWidget(self.second_thr_lc_factor)
        
        self.confirm_button = bind_text(QPushButton(self), 'Apply sensor parameters')
        self.confirm_button.clicked.connect(self.confirm_changes)
        layout1.addWidget(self.confirm_button)

        # Connect signals
        self.rho.valueChanged.connect(self.enable_confirm_button)
        self.kin_visc.valueChanged.connect(self.enable_confirm_button)
        self.first_trq_arm_length.valueChanged.connect(self.enable_confirm_button)
        self.first_trq_lc_factor.valueChanged.connect(self.enable_confirm_button)
        self.first_thr_arm_length.valueChanged.connect(self.enable_confirm_button)
        self.first_thr_lc_factor.valueChanged.connect(self.enable_confirm_button)
        self.second_trq_arm_length.valueChanged.connect(self.enable_confirm_button)
        self.second_trq_lc_factor.valueChanged.connect(self.enable_confirm_button)
        self.second_thr_arm_length.valueChanged.connect(self.enable_confirm_button)
        self.second_thr_lc_factor.valueChanged.connect(self.enable_confirm_button)
        self.probe_offset.valueChanged.connect(self.enable_confirm_button)
        

    def set_tandem_flag(self):
        # This checkbox edits a draft; READY commits the controller's configuration.
        self.probe_offset.setEnabled(self.tandem.isChecked())
        self.enable_confirm_button()
        
    def enable_confirm_button(self):
        if self._pending_values is not None:
            return
        self.confirm_button.setEnabled(True)
        self.confirm_button.setStyleSheet("background-color: orange; color: black;")

    def _set_pending(self, pending):
        for widget in self.findChildren(QDoubleSpinBox) + self.findChildren(QCheckBox):
            widget.setEnabled(not pending)
        self.probe_offset.setEnabled(not pending and self.tandem.isChecked())
        self.confirm_button.setEnabled(not pending)

    def confirm_changes(self):
        if self._pending_values is not None:
            return
        values = {
            "rho": self.rho.value(),
            "kin_visc": self.kin_visc.value(),
            "probe_offset": self.probe_offset.value(),
            "first_trq_arm_length": self.first_trq_arm_length.value(),
            "first_thr_arm_length": self.first_thr_arm_length.value(),
            "first_trq_cal_val": self.first_trq_lc_factor.value(),
            "first_thr_cal_val": self.first_thr_lc_factor.value(),
            "second_trq_arm_length": self.second_trq_arm_length.value(),
            "second_thr_arm_length": self.second_thr_arm_length.value(),
            "second_trq_cal_val": self.second_trq_lc_factor.value(),
            "second_thr_cal_val": self.second_thr_lc_factor.value(),
            "no_of_props": 2 if self.tandem.isChecked() else 1,
        }
        init_data = 'init|%.2f|%.2f|%.2f|%.2f|%.2f|%.2f|%.2f|%.2f|%d' % (
            values["first_trq_arm_length"], values["first_thr_arm_length"],
            values["first_trq_cal_val"], values["first_thr_cal_val"],
            values["second_trq_arm_length"], values["second_thr_arm_length"],
            values["second_trq_cal_val"], values["second_thr_cal_val"],
            values["no_of_props"],
        )
        self._pending_values = values
        self._set_pending(True)
        self.confirm_button.setStyleSheet("background-color: None; color: None;")
        app_globals.window.params.setStyleSheet("background-color: orange; color: black;")
        bind_text(app_globals.window.params, 'Please wait...')
        # Sending may fail synchronously; set the pending UI before emitting.
        self.sendData.emit(init_data)

    @pyqtSlot()
    def on_init_failed(self):
        self._pending_values = None
        self._set_pending(False)
        self.enable_confirm_button()

    @pyqtSlot()
    def on_init_ready(self):
        if self._pending_values is None:
            return
        for name, value in self._pending_values.items():
            setattr(self.shared_data, name, value)
        self._pending_values = None
        window = app_globals.window
        window.tandem_setup = self.shared_data.no_of_props == 2
        window.second_throttle.setEnabled(window.tandem_setup)
        window.label7.setEnabled(window.tandem_setup)
        # Axis parameters must be applied before enabling homing/file selection.
        window.homing.setEnabled(False)
        window.file.setEnabled(False)
        window.calibrate_second_loadcells_action.setEnabled(False)
        window.rpm_second_controller_action.setEnabled(False)
        self._set_pending(False)
        self.confirm_button.setEnabled(False)
        self.close()
