"""Thread-safe StandLink diagnostics and semantic operation/stream monitoring."""

import logging
import math
import threading
import time
from protocol.codec import unpack
from protocol.messages import MessageId


class SerialMonitor:
    def __init__(self, logger, clock=time.monotonic, silence_seconds=5.0):
        self.logger = logger
        self.clock = clock
        self.silence_seconds = silence_seconds
        self._lock = threading.RLock()
        self.connected = False
        self.port = None
        self._ports = None
        self._pending = {}
        self._last_warning = {}
        self._raw = False
        self._stream = None
        self._last_tx = None
        self._last_unterminated = False
        self._framing_warned = False
        self._gap_warned = False
        self._last_stream = self.clock()
        self._last_rx = self.clock()
        self._summary_at = self.clock()
        self._bytes = self._frames = self._invalid = 0

    def set_raw_logging(self, enabled):
        with self._lock:
            self._raw = bool(enabled)
            self.logger.info("Raw serial RX logging %s", "enabled" if enabled else "disabled")

    def port_opened(self, port):
        with self._lock:
            self.port, self.connected = port, True
            self._pending.clear()
            self._stream = None
            self._last_tx = None
            self._gap_warned = False
            self._last_warning.clear()
            self._last_rx = self._summary_at = self.clock()
            self._bytes = self._frames = self._invalid = 0
            self.logger.info("SERIAL CONNECTED port=%s baud=115200 read_timeout=0.1 write_timeout=1.0", port)

    def transport_error(self, message):
        with self._lock:
            self.logger.error("SERIAL I/O FAILURE port=%s: %s; connection lost or device/driver unavailable", self.port, message)
            self.connected = False
            self._pending.clear()
            self._stream = None

    def port_closed(self):
        with self._lock:
            if self.connected:
                self.logger.info("SERIAL CLOSED port=%s", self.port)
            self.connected = False
            self._pending.clear()
            self._stream = None

    def ports_changed(self, ports):
        with self._lock:
            current = set(ports)
            previous = self._ports
            if previous is not None:
                for port in sorted(previous - current):
                    self.logger.log(logging.ERROR if port == self.port else logging.INFO,
                                    "PORT DISAPPEARED %s%s", port,
                                    " (selected device; possible USB disconnect/reset)" if port == self.port else "")
                for port in sorted(current - previous):
                    self.logger.info("PORT APPEARED %s; reconnect manually if this is the controller", port)
            self._ports = current

    def bytes_received(self, count):
        with self._lock:
            self._bytes += count
            self._last_rx = self.clock()

    def protocol_error(self, message):
        with self._lock:
            self._invalid += 1
            self._warn_limited("invalid", "PROTOCOL invalid/incomplete frame: %s", message)

    def _warn_limited(self, key, message, *args):
        now = self.clock()
        if now - self._last_warning.get(key, float("-inf")) >= 10.0:
            self._last_warning[key] = now
            self.logger.warning(message, *args)

    def command_sent(self, command):
        if not command:
            return
        with self._lock:
            now = self.clock()
            self.logger.info("TX port=%s %r", self.port, command)
            name = command.strip().split("|", 1)[0]
            replies = {
                "home": ("homing done", 95), "j": ("jog done", 95),
                "center": ("centering done", 95), "tare": ("tare done", 20),
                "init": ("ready!", 30), "stop": ("ok|stopping", 5),
                "readAoA": ("readaoa|", 5), "readAoSS": ("readaoss|", 5),
            }
            if name in replies:
                reply, timeout = replies[name]
                if reply in self._pending:
                    self._warn_limited("overlap", "PROTOCOL command repeated before reply: %r", command)
                else:
                    self._pending[reply] = (command, now, timeout, False)
            if name in ("m", "ON"):
                self._stream = "measurements:" if name == "m" else "lc test:"
                self._last_stream = now
                self._gap_warned = False
            elif name in ("home", "j", "center", "tare", "stop", "OFF"):
                self._stream = None

    def command_rejected(self, command):
        with self._lock:
            for reply, pending in list(self._pending.items()):
                if pending[0] == command:
                    del self._pending[reply]
            if command.split('|', 1)[0] in ('m', 'ON'):
                self._stream = None

    def received_packet(self, packet):
        with self._lock:
            if self._raw:
                self.logger.debug("RX PACKET seq=%d id=%d payload=%s", packet.sequence, packet.message_id, packet.payload.hex())
            if packet.message_id == MessageId.HEARTBEAT:
                values = unpack(packet)
                counters = values[2:]
                previous = getattr(self, "_device_counters", None)
                if counters != previous and any(counters):
                    self.logger.warning("CONTROLLER LINK counters: CRC=%d estimated_sequence_gaps=%d duplicates=%d TX_errors=%d", *counters)
                self._device_counters = counters

    def received_line(self, text):
        with self._lock:
            now = self.clock()
            lower = text.lower()
            if self._raw:
                self.logger.debug("RX %r", text)
            matched_reply = False
            for reply in list(self._pending):
                if lower.startswith(reply):
                    command, started, _, warned = self._pending.pop(reply)
                    matched_reply = True
                    self.logger.info("REPLY%s to %r after %.3f s: %s", " LATE" if warned else "", command, now - started, text)
            telemetry = next((p for p in ("measurements:", "lc test:") if lower.startswith(p)), None)
            if telemetry:
                expected = 13 if telemetry == "measurements:" else 10
                fields = text.split(":", 1)[1].split()
                try:
                    values = [float(x) for x in fields]
                    if len(values) != expected or not all(math.isfinite(x) for x in values):
                        raise ValueError(f"expected {expected} finite numeric fields")
                    if telemetry == "measurements:" and any(abs(x) > 2147483647 for x in values[:2]):
                        raise ValueError("position outside Qt integer range")
                except ValueError as exc:
                    self.protocol_error(f"{exc}; RX={text[:512]!r}")
                    return
                self._frames += 1
                if telemetry == self._stream:
                    if self._gap_warned:
                        self.logger.info("TELEMETRY RESUMED after %.1f s", now - self._last_stream)
                    self._last_stream = now
                    self._gap_warned = False
                return
            if lower.startswith(("pitot:", "pitotlive|")):
                return
            if ("emergency!" in lower or "safety switch disconnected" in lower
                    or "|err" in lower or lower.startswith("err|")
                    or lower in ("limit switch", "over axis limit")):
                self._warn_limited(lower[:80], "FIRMWARE %s", text)
            elif text and not matched_reply:
                self.logger.info("FIRMWARE %s", text)
            if lower.startswith("aoss boot zero"):
                self.logger.warning("CONTROLLER BOOT message observed; possible reset/restart")
            if lower in ("limit switch", "over axis limit", "emergency!"):
                self._stream = None

    def tick(self):
        with self._lock:
            if not self.connected:
                return
            now = self.clock()
            for reply, (command, started, timeout, warned) in list(self._pending.items()):
                if not warned and now - started >= timeout:
                    self.logger.warning("REPLY TIMEOUT after %.1f s: TX=%r expected=%r; possible lost command/reply or controller stall", now - started, command, reply)
                    self._pending[reply] = (command, started, timeout, True)
            if self._stream and not self._gap_warned and now - self._last_stream >= self.silence_seconds:
                self.logger.warning("TELEMETRY GAP: no valid %s frame for %.1f s; last serial bytes %.1f s ago; possible interruption, not confirmed packet loss", self._stream, now - self._last_stream, now - self._last_rx)
                self._gap_warned = True
            if now - self._summary_at >= 30:
                self.logger.info("SERIAL SUMMARY port=%s bytes=%d valid_frames=%d protocol_issues=%d awaiting_replies=%d last_rx_age=%.1fs", self.port, self._bytes, self._frames, self._invalid, len(self._pending), now - self._last_rx)
                self._summary_at = now
