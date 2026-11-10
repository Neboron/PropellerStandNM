"""Transport-independent StandLink framing. No Qt, serial, or stand dependencies."""
from dataclasses import dataclass

STX = 0x42
SYSTEM_ID = 1
MAX_PAYLOAD = 255
MAX_FRAME = MAX_PAYLOAD + 7


def crc16(data, initial=0xFFFF):
    """CRC-16/MCRF4XX: reflected 0x1021, init FFFF, no final XOR."""
    crc = initial
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (0x8408 if crc & 1 else 0)
    return crc


@dataclass(frozen=True)
class Packet:
    sequence: int
    system_id: int
    message_id: int
    payload: bytes


def encode(packet, crc_extra=0):
    if len(packet.payload) > MAX_PAYLOAD:
        raise ValueError('payload exceeds 255 bytes')
    header = bytes((len(packet.payload), packet.sequence, packet.system_id, packet.message_id))
    body = header + packet.payload
    checksum = crc16(bytes((crc_extra,)), crc16(body))
    return bytes((STX,)) + body + checksum.to_bytes(2, 'little')


class Decoder:
    """Bounded incremental decoder with CRC-verified resynchronization.

    specs(id) -> (payload length or None for variable length, CRC extra), or None
    for an unknown ID. Caller owns timeouts and transport; feed accepts any chunk.
    A complete, valid leading packet owns its payload (including embedded STX).
    An incomplete prefix is abandoned only after the inter-byte timeout, so
    arbitrary payload bytes cannot be mistaken for a nested packet.
    """
    def __init__(self, specs, system_id=SYSTEM_ID, timeout=0.5):
        self.specs = specs
        self.system_id = system_id
        self.timeout = timeout
        self.buffer = bytearray()
        self.last_byte_time = None
        self.crc_errors = 0
        self.discarded_bytes = 0
        self.timeouts = 0

    def feed(self, data, now=0.0):
        packets = self.expire(now)
        for byte in data:
            self.buffer.append(byte)
            self.last_byte_time = now
            packets.extend(self._drain())
        return packets

    def expire(self, now):
        if self.buffer and self.last_byte_time is not None and now - self.last_byte_time >= self.timeout:
            self.timeouts += 1
            # Drop only the truncated candidate's STX, then search retained bytes.
            self.discarded_bytes += 1
            del self.buffer[0]
            result = self._drain(recovering=True)
            self.discarded_bytes += len(self.buffer)
            self.buffer.clear()
            return result
        return []

    def _candidate(self, offset):
        remaining = len(self.buffer) - offset
        if remaining < 5:
            return 'partial', 0
        length, _, sysid, msgid = self.buffer[offset + 1:offset + 5]
        spec = self.specs(msgid)
        if sysid != self.system_id or spec is None or (spec[0] is not None and spec[0] != length):
            return 'invalid', 0
        total = length + 7
        if remaining < total:
            return 'partial', total
        body = self.buffer[offset + 1:offset + total - 2]
        expected = crc16(bytes((spec[1],)), crc16(body))
        actual = int.from_bytes(self.buffer[offset + total - 2:offset + total], 'little')
        return ('valid' if expected == actual else 'crc'), total

    def _drain(self, recovering=False):
        result = []
        while self.buffer:
            if self.buffer[0] != STX:
                self.discarded_bytes += 1
                del self.buffer[0]
                continue
            state, total = self._candidate(0)
            if state == 'partial':
                if not recovering:
                    break
                self.discarded_bytes += 1
                del self.buffer[0]
                continue
            if state != 'valid':
                self.crc_errors += state == 'crc'
                self.discarded_bytes += 1
                del self.buffer[0]
                continue
            result.append(Packet(self.buffer[2], self.buffer[3], self.buffer[4], bytes(self.buffer[5:total - 2])))
            del self.buffer[:total]
        return result


class SequenceTracker:
    """One ordered point-to-point stream; modulo-256 gaps are estimates.
    """
    def __init__(self):
        self.last = None
        self.gaps = 0
        self.duplicates = 0

    def observe(self, packet):
        if packet == self.last:
            self.duplicates += 1
            return False
        if self.last is not None:
            delta = (packet.sequence - self.last.sequence) & 255
            if delta != 1:
                self.gaps += (delta - 1) & 255
        self.last = packet
        return True
