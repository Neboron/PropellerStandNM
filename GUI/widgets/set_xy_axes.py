import sys
from PyQt5.QtCore import pyqtSignal, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QDoubleSpinBox, QSpinBox, QPushButton, QRadioButton, QGroupBox, QHBoxLayout, QCheckBox
import serial
import app_globals
from i18n import bind_text

class SetXYAxes(QWidget):
    sendData = pyqtSignal(str)
    centerStepsChanged = pyqtSignal(int)

    def __init__(self, shared_data):
        super().__init__()
        self.shared_data = shared_data
        layout1 = QVBoxLayout(); self.setLayout(layout1)
        bind_text(self, 'Axis parameters', property_name="windowTitle")
        
        rot_group = bind_text(QGroupBox(), 'Rotation direction', property_name='title')
        rot_layout = QHBoxLayout(rot_group)
        self.rot_cw  = bind_text(QRadioButton(), 'CW (clockwise)')
        self.rot_ccw = bind_text(QRadioButton(), 'CCW (counterclockwise)')
        rot_layout.addWidget(self.rot_cw)
        rot_layout.addWidget(self.rot_ccw)
        layout1.addWidget(rot_group)

        # default from shared_data if present
        dir0 = getattr(self.shared_data, "rotation_dir", 0)
        if dir0 == -1: self.rot_cw.setChecked(True)
        elif dir0 == 1: self.rot_ccw.setChecked(True)

        # ensure confirm stays disabled until a choice is made
        def _on_rotation_changed():
            self.enable_confirm_axis_button()
        self.rot_cw.toggled.connect(_on_rotation_changed)
        self.rot_ccw.toggled.connect(_on_rotation_changed)
        
        self.aoss_enabled_button = bind_text(QCheckBox(self), 'Enable AoSS axis')
        try:
            self.aoss_enabled_button.setChecked(bool(self.shared_data.aoss_enabled))
        except Exception:
            self.aoss_enabled_button.setChecked(False)
        layout1.addWidget(self.aoss_enabled_button)
        
        self.label33 = bind_text(QLabel(), 'Safety margin (% of propeller radius)')
        layout1.addWidget(self.label33)
        
        self.safety_o_prop = QSpinBox()
        self.safety_o_prop.setMinimum(0)
        self.safety_o_prop.setMaximum(15)
        self.safety_o_prop.setSingleStep(1)
        self.safety_o_prop.setValue(self.shared_data.safety_over_prop)
        layout1.addWidget(self.safety_o_prop)
        
        self.label34 = bind_text(QLabel(), 'Measurement resolution (mm)')
        layout1.addWidget(self.label34)
        
        self.x_delta = QSpinBox()
        self.x_delta.setMinimum(1)
        self.x_delta.setMaximum(20)
        self.x_delta.setSingleStep(1)
        self.x_delta.setValue(self.shared_data.x_delta)
        layout1.addWidget(self.x_delta)
        
        self.label35 = bind_text(QLabel(), 'Maximum number of measurements')
        layout1.addWidget(self.label35)
        
        self.max_number_of_samples = QSpinBox()
        self.max_number_of_samples.setMinimum(1)
        self.max_number_of_samples.setMaximum(30)
        self.max_number_of_samples.setSingleStep(1)
        self.max_number_of_samples.setValue(self.shared_data.max_number_of_samples)
        layout1.addWidget(self.max_number_of_samples)
        
        self.label30 = bind_text(QLabel(), 'Stepper drive ratio (steps/mm)')
        layout1.addWidget(self.label30)
        
        self.ratio = QDoubleSpinBox()
        self.ratio.setMinimum(0)
        self.ratio.setDecimals(4)
        self.ratio.setSingleStep(0.0001)
        self.ratio.setValue(self.shared_data.ratio)
        layout1.addWidget(self.ratio)
        
        self.label36 = bind_text(QLabel(), 'X-axis motor center (maximum travel) (mm)')
        layout1.addWidget(self.label36)
        
        self.x_center = QDoubleSpinBox()
        self.x_center.setMinimum(1)
        self.x_center.setMaximum(330)
        self.x_center.setSingleStep(0.1)
        self.x_center.setValue(self.shared_data.x_center)
        layout1.addWidget(self.x_center)
        
        self.label37 = bind_text(QLabel(), 'Y-axis maximum travel (mm)')
        layout1.addWidget(self.label37)
        
        self.y_max = QSpinBox()
        self.y_max.setMinimum(1)
        self.y_max.setMaximum(107)
        self.y_max.setSingleStep(1)
        self.y_max.setValue(self.shared_data.y_max)
        layout1.addWidget(self.y_max)
        
        self.label38 = bind_text(QLabel(), 'X-axis maximum speed (steps/s)')
        layout1.addWidget(self.label38)
        
        self.x_max_speed = QSpinBox()
        self.x_max_speed.setMinimum(100)
        self.x_max_speed.setMaximum(2000)
        self.x_max_speed.setSingleStep(100)
        self.x_max_speed.setValue(self.shared_data.x_max_speed)
        layout1.addWidget(self.x_max_speed)
        
        self.label39 = bind_text(QLabel(), 'Y-axis maximum speed (steps/s)')
        layout1.addWidget(self.label39)
        
        self.y_max_speed = QSpinBox()
        self.y_max_speed.setMinimum(100)
        self.y_max_speed.setMaximum(2000)
        self.y_max_speed.setSingleStep(100)
        self.y_max_speed.setValue(self.shared_data.y_max_speed)
        layout1.addWidget(self.y_max_speed)
        
        self.label40 = bind_text(QLabel(), 'X-axis maximum acceleration (steps/s/s)')
        layout1.addWidget(self.label40)
        
        self.x_max_accel = QSpinBox()
        self.x_max_accel.setMinimum(50)
        self.x_max_accel.setMaximum(1500)
        self.x_max_accel.setSingleStep(100)
        self.x_max_accel.setValue(self.shared_data.x_max_accel)
        layout1.addWidget(self.x_max_accel)
        
        self.label41 = bind_text(QLabel(), 'Y-axis maximum acceleration (steps/s/s)')
        layout1.addWidget(self.label41)
        
        self.y_max_accel = QSpinBox()
        self.y_max_accel.setMinimum(50)
        self.y_max_accel.setMaximum(1500)
        self.y_max_accel.setSingleStep(100)
        self.y_max_accel.setValue(self.shared_data.y_max_accel)
        layout1.addWidget(self.y_max_accel)
        
        self.confirm_axis_button = bind_text(QPushButton(self), 'Apply axis parameters')
        self.confirm_axis_button.clicked.connect(self.confirm_axis_changes)
        self.confirm_axis_button.setEnabled(False)
        layout1.addWidget(self.confirm_axis_button)
        
        self.safety_o_prop.valueChanged.connect(self.enable_confirm_axis_button)
        self.x_delta.valueChanged.connect(self.enable_confirm_axis_button)
        self.max_number_of_samples.valueChanged.connect(self.enable_confirm_axis_button)
        self.ratio.valueChanged.connect(self.enable_confirm_axis_button)
        self.x_center.valueChanged.connect(self.enable_confirm_axis_button)
        self.y_max.valueChanged.connect(self.enable_confirm_axis_button)
        self.x_max_speed.valueChanged.connect(self.enable_confirm_axis_button)
        self.y_max_speed.valueChanged.connect(self.enable_confirm_axis_button)
        self.x_max_accel.valueChanged.connect(self.enable_confirm_axis_button)
        self.y_max_accel.valueChanged.connect(self.enable_confirm_axis_button)
        self.aoss_enabled_button.stateChanged.connect(self.send_aoss_enable_flag)  
        
    def enable_confirm_axis_button(self):
        self.confirm_axis_button.setEnabled(True)
        self.confirm_axis_button.setStyleSheet("background-color: orange; color: black;")
    
    def confirm_axis_changes(self):
        try:
            if not (self.rot_cw.isChecked() or self.rot_ccw.isChecked()):
                # require explicit choice
                self.confirm_axis_button.setEnabled(False)
                #self.confirm_axis_button.setStyleSheet("background-color: ; color: white;")
                return

            self.shared_data.rotation_dir = -1 if self.rot_cw.isChecked() else 1
            print(self.shared_data.rotation_dir)
            if not hasattr(self.shared_data, "mount_sign"):
                self.shared_data.mount_sign = 1  # later flip to -1 if S-test says so
        
            self.shared_data.safety_over_prop = self.safety_o_prop.value()
            self.shared_data.x_delta = self.x_delta.value()
            self.shared_data.max_number_of_samples = self.max_number_of_samples.value()
            self.shared_data.ratio = self.ratio.value()
            self.shared_data.x_center = self.x_center.value()
            self.shared_data.y_max = self.y_max.value()
            self.shared_data.x_max_speed = self.x_max_speed.value()
            self.shared_data.y_max_speed = self.y_max_speed.value()
            self.shared_data.x_max_accel = self.x_max_accel.value()
            self.shared_data.y_max_accel = self.y_max_accel.value()
            
            limit_data = 'l|%d|%d|%d|%d|%d|%d' % (
                (self.shared_data.x_center * self.shared_data.ratio), (self.shared_data.y_max * self.shared_data.ratio),
                self.shared_data.x_max_speed, self.shared_data.y_max_speed, self.shared_data.x_max_accel,
                self.shared_data.y_max_accel
                )
            self.sendData.emit(limit_data)
            
            x_center_steps = int(self.shared_data.x_center * self.shared_data.ratio)
            self.centerStepsChanged.emit(x_center_steps)
            
            self.confirm_axis_button.setEnabled(True)
            self.confirm_axis_button.setStyleSheet("background-color: None; color: None;")
            if app_globals.window.tandem_setup:
                app_globals.window.file.setEnabled(False)
                app_globals.window.homing.setEnabled(True)
            else:
                app_globals.window.file.setEnabled(True)
                app_globals.window.homing.setEnabled(app_globals.window.fileSelected)
            QTimer.singleShot(1000, self.close)
            app_globals.window.aoa_aoss_action.setEnabled(True)
            app_globals.window.calibrate_first_loadcells_action.setEnabled(True)
            app_globals.window.calibrate_second_loadcells_action.setEnabled(app_globals.window.tandem_setup)
            app_globals.window.rpm_second_controller_action.setEnabled(app_globals.window.tandem_setup)
            app_globals.window.rpm_first_controller_action.setEnabled(True)
            app_globals.window.map_action.setEnabled(True)
            app_globals.window.clear_plot_action.setEnabled(True)
            app_globals.window.save_plot_action.setEnabled(True)
            QTimer.singleShot(1000, self.close)
            app_globals.window.xy_axes.setStyleSheet("background-color: green; color: white;")
            bind_text(app_globals.window.xy_axes, 'Axis settings ✓')
        except serial.SerialException as e:
            print(f"Error sending data: {e}")
            
    def send_aoss_enable_flag(self, state):
        try:
            enabled = (state == 2)  # Qt.Checked == 2
            # Persist in SharedData
            try:
                self.shared_data.aoss_enabled = enabled
            except Exception:
                pass
            # Then command MCU
            if enabled:
                self.sendData.emit("enableAoSS")
            else:
                self.sendData.emit("disableAoSS")
        except Exception:
            print("AoSS set failed")
