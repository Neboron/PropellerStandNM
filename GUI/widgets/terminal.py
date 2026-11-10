"""Read-only diagnostics tab; no serial-port ownership or command execution."""

import logging
from PyQt5.QtCore import QTimer, QUrl, Qt
from PyQt5.QtGui import QColor, QDesktopServices, QFontDatabase, QTextCharFormat, QTextCursor
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QHBoxLayout, QLabel,
    QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)
from i18n import bind_text, language_manager, tr


class TerminalWidget(QWidget):
    def __init__(self, diagnostics, monitor, parent=None):
        super().__init__(parent)
        self.diagnostics = diagnostics
        self._sequence = self._cleared_at = 0
        layout = QVBoxLayout(self)
        self.path_label = bind_text(QLabel(), "Log folder: {path}", path=str(diagnostics.directory))
        self.path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.path_label.setWordWrap(True)
        layout.addWidget(self.path_label)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        controls = QHBoxLayout()
        self.level = QComboBox()
        self.level.addItem("", logging.DEBUG)
        self.level.addItem("", logging.WARNING)
        controls.addWidget(self.level)
        self.pause = bind_text(QCheckBox(), "Pause display")
        controls.addWidget(self.pause)
        self.follow = bind_text(QCheckBox(), "Follow latest")
        self.follow.setChecked(True)
        controls.addWidget(self.follow)
        controls.addStretch()
        self.copy_button = bind_text(QPushButton(), "Copy log")
        self.copy_button.clicked.connect(self.copy_log)
        controls.addWidget(self.copy_button)
        self.clear_button = bind_text(QPushButton(), "Clear view")
        self.clear_button.clicked.connect(self.clear_view)
        controls.addWidget(self.clear_button)
        self.folder_button = bind_text(QPushButton(), "Open log folder")
        self.folder_button.clicked.connect(self.open_folder)
        controls.addWidget(self.folder_button)
        layout.addLayout(controls)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumBlockCount(5000)
        self.output.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.output.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
        self.output.setStyleSheet("QPlainTextEdit { background: #101820; color: #d9e2ec; border: 1px solid #34495e; padding: 8px; }")
        layout.addWidget(self.output, 1)
        self.raw = bind_text(QCheckBox(), "Record raw serial traffic (larger log files)")
        self.raw.toggled.connect(monitor.set_raw_logging)
        layout.addWidget(self.raw)
        self.level.currentIndexChanged.connect(self.refresh_history)
        language_manager().changed.connect(self.refresh_labels)
        self.refresh_labels()
        self.timer = QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.poll)
        self.timer.start()

    def refresh_labels(self):
        self.level.setItemText(0, tr("All messages"))
        self.level.setItemText(1, tr("Warnings and errors"))
        self.update_status()

    def update_status(self):
        error = self.diagnostics.save_error
        self.status.setText(error)
        self.status.setVisible(bool(error))
        self.status.setStyleSheet("color: #d64545;" if error else "")

    def _append(self, text, level):
        color = "#ff8a80" if level >= logging.ERROR else "#ffd180" if level >= logging.WARNING else "#d9e2ec"
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor = QTextCursor(self.output.document())
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text + "\n", fmt)

    def poll(self):
        self.update_status()
        if self.pause.isChecked():
            return
        entries = self.diagnostics.entries_after(self._sequence)
        if not entries:
            return
        bar = self.output.verticalScrollBar()
        position = bar.value()
        if entries[0].sequence > self._sequence + 1:
            self._append(tr("Older messages left the display buffer; see the saved log files."), logging.WARNING)
        for entry in entries[:500]:
            if entry.level >= self.level.currentData():
                self._append(entry.text, entry.level)
            self._sequence = entry.sequence
        bar.setValue(bar.maximum() if self.follow.isChecked() else position)

    def refresh_history(self):
        self.output.clear()
        self._sequence = self._cleared_at
        self.poll()

    def clear_view(self):
        entries = self.diagnostics.entries_after()
        self._cleared_at = entries[-1].sequence if entries else self._sequence
        self._sequence = self._cleared_at
        self.output.clear()

    def copy_log(self):
        selected = self.output.textCursor().selectedText().replace("\u2029", "\n")
        QApplication.clipboard().setText(selected or self.output.toPlainText())

    def open_folder(self):
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.diagnostics.directory))):
            self.diagnostics.logger.warning("Could not open log folder: %s", self.diagnostics.directory)
