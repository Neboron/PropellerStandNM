"""Optional application-boundary hooks; the logging service stays Qt-free."""

import logging
import sys
import threading
from PyQt5.QtCore import QtDebugMsg, QtInfoMsg, QtWarningMsg, QtFatalMsg, qInstallMessageHandler


def install_runtime_logging(diagnostics):
    """Capture Python tracebacks and Qt diagnostics; return a restoration hook."""
    logger = diagnostics.logger
    original_exception = sys.excepthook
    original_thread_exception = threading.excepthook

    def exception_hook(kind, value, traceback):
        logger.critical("Unhandled Python exception", exc_info=(kind, value, traceback))
        diagnostics.flush()
        original_exception(kind, value, traceback)

    def thread_exception_hook(args):
        logger.critical("Unhandled exception in thread %s", args.thread.name if args.thread else "unknown",
                        exc_info=(args.exc_type, args.exc_value, args.exc_traceback))
        original_thread_exception(args)

    def qt_message(kind, context, message):
        level = {QtDebugMsg: logging.DEBUG, QtInfoMsg: logging.INFO, QtWarningMsg: logging.WARNING}.get(kind, logging.ERROR)
        logger.log(level, "QT %s (%s:%s)", message, context.file or "unknown", context.line)
        if kind == QtFatalMsg:
            diagnostics.flush()
        if original_qt:
            original_qt(kind, context, message)

    original_qt = qInstallMessageHandler(qt_message)
    sys.excepthook = exception_hook
    threading.excepthook = thread_exception_hook

    def restore():
        sys.excepthook = original_exception
        threading.excepthook = original_thread_exception
        qInstallMessageHandler(original_qt)

    return restore
