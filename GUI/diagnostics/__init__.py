"""Independent logging and serial-protocol diagnostics (no Qt dependency)."""

from .log import DiagnosticLog
from .serial_monitor import SerialMonitor

__all__ = ["DiagnosticLog", "SerialMonitor"]
