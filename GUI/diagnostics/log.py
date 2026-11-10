"""Bounded, asynchronous diagnostics with an append-only file per local date."""

from collections import deque
from dataclasses import dataclass
from datetime import datetime
import logging
from logging.handlers import QueueHandler, QueueListener
import os
import platform
from pathlib import Path
import queue
import threading
import time
import uuid


@dataclass(frozen=True)
class LogEntry:
    sequence: int
    level: int
    text: str


class _LocalTimeFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        return datetime.fromtimestamp(record.created).astimezone().isoformat(timespec="milliseconds")


class _QueueHandler(QueueHandler):
    def __init__(self, owner, records):
        super().__init__(records)
        self.owner = owner

    def enqueue(self, record):
        try:
            self.queue.put_nowait(record)
        except queue.Full:
            with self.owner._lock:
                self.owner._dropped += 1


class _Listener(QueueListener):
    def enqueue_sentinel(self):
        # Shutdown drains even a full queue instead of losing the tail of a log.
        self.queue.put(self._sentinel)


class _DailySink(logging.Handler):
    """Only the QueueListener thread accesses the file handle."""

    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.stream = None
        self.day = None
        self.retry_at = 0.0
        self.setFormatter(_LocalTimeFormatter("%(asctime)s %(levelname)-8s %(message)s"))

    def emit(self, record):
        owner = self.owner
        with owner._lock:
            dropped, owner._dropped = owner._dropped, 0
        if dropped:
            warning = logging.LogRecord("diagnostics", logging.ERROR, "", 0,
                                        "LOG OVERLOAD: %d records dropped; diagnostics incomplete",
                                        (dropped,), None)
            self._write_record(warning)
        self._write_record(record)

    def _write_record(self, record):
        owner = self.owner
        text = self.format(record)
        owner._append(record.levelno, text)
        if time.monotonic() < self.retry_at:
            return
        try:
            day = datetime.fromtimestamp(record.created).astimezone().date().isoformat()
            if self.stream is None or day != self.day:
                if self.stream:
                    self.stream.close()
                    self.stream = None
                owner.directory.mkdir(parents=True, exist_ok=True)
                self.stream = (owner.directory / f"{day}.log").open("a", encoding="utf-8")
                self.day = day
            self.stream.write(text + "\n")
            self.stream.flush()
            self.retry_at = 0.0
            if owner.save_error:
                recovery = "Log file saving recovered; records during the failure may be missing."
                self.stream.write(recovery + "\n")
                self.stream.flush()
                owner._append(logging.INFO, recovery)
                owner._set_save_error("")
        except (OSError, UnicodeError) as exc:
            if self.stream:
                try:
                    self.stream.close()
                except OSError:
                    pass
            self.stream = None
            self.retry_at = time.monotonic() + 30.0
            message = f"LOG SAVE FAILED: {exc}. Retrying on a later message in 30 s."
            owner._set_save_error(message)
            owner._append(logging.ERROR, message)

    def close(self):
        if self.stream:
            try:
                self.stream.close()
            except OSError as exc:
                self.owner._set_save_error(f"Log close failed: {exc}")
            self.stream = None
        super().close()


class DiagnosticLog:
    """Owns one session. Producers use ``logger``; views poll ``entries_after``.

    File I/O never runs in the GUI or serial-reader thread. The queue and visible
    history are bounded; overload and saving failures are explicitly reported.
    Files use the event's local date and append across application restarts.
    """

    def __init__(self, directory=None, history_limit=5000, queue_limit=10000):
        default = Path.home() / "Desktop" / "logid" / "diagnostics"
        self.directory = Path(directory or os.environ.get("PROPELLER_DIAGNOSTIC_LOG_DIR", default)).expanduser().resolve()
        self.session_id = uuid.uuid4().hex[:8]
        self._lock = threading.Lock()
        self._history = deque(maxlen=history_limit)
        self._sequence = 0
        self._dropped = 0
        self._save_error = ""
        self._closed = False
        self._records = queue.Queue(maxsize=queue_limit)
        self.logger = logging.Logger(f"propeller.{self.session_id}", level=logging.DEBUG)
        self.logger.propagate = False
        self._handler = _QueueHandler(self, self._records)
        self.logger.addHandler(self._handler)
        self._sink = _DailySink(self)
        self._listener = _Listener(self._records, self._sink)
        self._listener.start()
        self.logger.info("SESSION START id=%s pid=%d log_directory=%s", self.session_id, os.getpid(), self.directory)
        self.logger.info("ENVIRONMENT os=%s %s python=%s", platform.system(), platform.release(), platform.python_version())

    def _append(self, level, text):
        with self._lock:
            self._sequence += 1
            self._history.append(LogEntry(self._sequence, level, text))

    def _set_save_error(self, message):
        with self._lock:
            self._save_error = message

    @property
    def save_error(self):
        with self._lock:
            return self._save_error

    def entries_after(self, sequence=0):
        with self._lock:
            return [entry for entry in self._history if entry.sequence > sequence]

    def flush(self):
        """Wait for queued records; intended for shutdown and deterministic tests."""
        self._records.join()

    def close(self):
        if self._closed:
            return
        self._closed = True
        self.logger.info("SESSION END id=%s", self.session_id)
        self._listener.stop()
        self.logger.removeHandler(self._handler)
        self._handler.close()
        self._sink.close()
