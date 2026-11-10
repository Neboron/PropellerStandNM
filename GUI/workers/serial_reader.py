"""Qt transport adapter for the reusable, bounded StandLink binary decoder."""
import time
from PyQt5.QtCore import QObject, pyqtSignal
from protocol.framing import Decoder, SequenceTracker
from protocol.codec import spec, unpack
from protocol.messages import DEFINITIONS


class SerialReader(QObject):
    packet_received = pyqtSignal(object)
    serial_error = pyqtSignal(str)
    protocol_error = pyqtSignal(str)
    bytes_received = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.running = True
        self.decoder = Decoder(spec)
        self.sequence = SequenceTracker()
        self._counters = (0, 0, 0, 0, 0)

    def run(self):
        try:
            if self.controller.timeout is None or self.controller.timeout > 0.1:
                self.controller.timeout = 0.1
            while self.running and self.controller.isOpen():
                n = int(self.controller.in_waiting or 0)
                data = self.controller.read(min(n, 4096) if n else 1)
                if data:
                    self.bytes_received.emit(len(data))
                    self._consume(data)
                self._check_partial_frame()
        except (OSError, ValueError) as exc:
            if self.running:
                self.serial_error.emit(f'{type(exc).__name__}: {exc}')
        finally:
            if self.decoder.buffer:
                self.protocol_error.emit(f'Reader stopped with {len(self.decoder.buffer)} incomplete packet bytes')
            self.running = False
            self.finished.emit()

    def _consume(self, data):
        self._deliver(self.decoder.feed(data, time.monotonic()))

    def _deliver(self, packets):
        for packet in packets:
            if not self.sequence.observe(packet):
                continue
            try:
                if DEFINITIONS[packet.message_id][4] != 'device':
                    raise ValueError('received host-only message (echo or wrong peer)')
                unpack(packet)
            except (ValueError, UnicodeDecodeError) as exc:
                self.protocol_error.emit(str(exc))
                continue
            self.packet_received.emit(packet)
        counters = (self.decoder.crc_errors, self.decoder.discarded_bytes,
                    self.decoder.timeouts, self.sequence.gaps, self.sequence.duplicates)
        if counters != self._counters:
            self.protocol_error.emit('StandLink counters: CRC=%d discarded_bytes=%d partial_timeouts=%d estimated_sequence_gaps=%d duplicates=%d' % counters)
            self._counters = counters

    def _check_partial_frame(self):
        self._deliver(self.decoder.expire(time.monotonic()))

    def stop(self):
        self.running = False
