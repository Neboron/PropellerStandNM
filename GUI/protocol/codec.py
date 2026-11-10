"""Typed message encoding, validation and application-independent packet access."""
import math
import struct
from enum import IntEnum
from .framing import Packet, encode
from .messages import DEFINITIONS, MessageId, VERSION, SCHEMA_HASH


class Result(IntEnum):
    ACCEPTED = 0
    INVALID = 1
    BAD_STATE = 2
    UNSUPPORTED = 3
    BUSY = 4
    FAILED = 5
    TIMEOUT = 6


class Event(IntEnum):
    READY = 0
    HOMED = 1
    JOG_DONE = 2
    CENTER_DONE = 3
    TARE_DONE = 4
    LIMIT_SWITCH = 5
    AXIS_LIMIT = 6
    EMERGENCY = 7
    EMERGENCY_CLEARED = 8
    SAFETY_OPEN = 9
    SAFETY_CLOSED = 10
    MOVE_DONE = 11
    MOVE_TIMEOUT = 12


def spec(message_id):
    entry = DEFINITIONS.get(message_id)
    if entry is None:
        return None
    return (struct.calcsize(entry[1]) if entry[1] is not None else None, entry[3])


def pack(message_id, *values, sequence=0, system_id=1):
    entry = DEFINITIONS.get(message_id)
    if entry is None:
        raise ValueError(f'unknown message ID {message_id}')
    if any(isinstance(v, float) and not math.isfinite(v) for v in values):
        raise ValueError('nonfinite payload value')
    try:
        payload = bytes(values[0]) if entry[1] is None and len(values)==1 else struct.pack(entry[1], *values)
    except (struct.error, TypeError, OverflowError) as exc:
        raise ValueError(f'{entry[0]}: invalid payload: {exc}') from exc
    if len(payload)>255:
        raise ValueError('payload exceeds 255 bytes')
    return Packet(sequence, system_id, int(message_id), payload)


def unpack(packet):
    entry = DEFINITIONS[packet.message_id]
    if entry[1] is None:
        return (packet.payload.decode('utf-8'),)
    try:
        values = struct.unpack(entry[1], packet.payload)
    except struct.error as exc:
        raise ValueError(f'{entry[0]}: invalid length') from exc
    if any(isinstance(v,float) and not math.isfinite(v) for v in values):
        raise ValueError(f'{entry[0]}: nonfinite payload')
    return values


def wire_bytes(packet):
    return encode(packet, DEFINITIONS[packet.message_id][3])
