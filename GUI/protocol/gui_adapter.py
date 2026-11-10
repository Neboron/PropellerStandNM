"""Compatibility at the GUI boundary only: existing Qt slots retain their names.

No text commands or telemetry lines cross the serial wire. New integrations use
codec.pack/unpack and MessageId directly. STATUS_TEXT cannot drive GUI state.
"""
from .codec import Event, pack, unpack
from .messages import MessageId as M

_SIMPLE = {
    'init': M.INIT, 'l': M.AXIS_LIMITS, 'home': M.HOME, 'j': M.JOG,
    'm': M.MEASURE_MOVE, 'center': M.CENTER, 'tare': M.TARE,
    'startMotor': M.START_MOTORS, 'stop': M.STOP, 'setMin': M.SET_MIN,
    'setMax': M.SET_MAX, 'setRamp': M.SET_RAMP, 'firstMotorTest': M.TEST_FIRST,
    'secondMotorTest': M.TEST_SECOND, 'props': M.PROPS, 'status': M.STATUS,
    'trimAoA': M.AOA_TRIM, 'AoAlim': M.AOA_LIMIT, 'AoAaxis': M.AOA_ENABLE,
    'readAoA': M.AOA_READ, 'trimAoSS': M.AOSS_TRIM, 'moveAoSS': M.AOSS_MOVE,
    'moveAoSSTubeAbs': M.AOSS_MOVE, 'moveAoSSServoAbs': M.AOSS_SERVO_MOVE,
    'setAoSSRatio': M.AOSS_RATIO, 'setAoSSLimits': M.AOSS_LIMITS,
    'readAoSS': M.AOSS_READ, 'zeroAoSS': M.AOSS_ZERO, 'aossDir': M.AOSS_DIRECTION,
    'aossCal': M.AOSS_CAL, 'aossTest': M.AOSS_TEST, 'setRunModeTurn': M.AOSS_TURN_SETUP,
    'getAoSSRatio': M.AOSS_CONFIG_GET, 'getAoSSLimits': M.AOSS_CONFIG_GET,
    'readPitotLive': M.PITOT_READ,
}
_TOGGLES = {
    'ON': (M.TEST_STREAM,1), 'OFF': (M.TEST_STREAM,0),
    'BeaconON': (M.BEACON,1), 'BeaconOFF': (M.BEACON,0),
    'enableAoSS': (M.AOSS_ENABLE,1), 'disableAoSS': (M.AOSS_ENABLE,0),
    'pitotLiveStart': (M.PITOT_STREAM,1), 'pitotLiveStop': (M.PITOT_STREAM,0),
    'pitotLiveHoldOn': (M.PITOT_HOLD,1), 'pitotLiveHoldOff': (M.PITOT_HOLD,0),
    'streamStart': (M.RAW_PITOT_STREAM,1), 'streamStop': (M.RAW_PITOT_STREAM,0),
}
EVENT_TEXT = {
    Event.READY: 'Ready!', Event.HOMED:'homing done', Event.JOG_DONE:'jog done',
    Event.CENTER_DONE:'centering done', Event.TARE_DONE:'tare done',
    Event.LIMIT_SWITCH:'limit switch', Event.AXIS_LIMIT:'over axis limit',
    Event.EMERGENCY:'Emergency!', Event.EMERGENCY_CLEARED:'Emergency cleared',
    Event.SAFETY_OPEN:'Safety switch disconnected!', Event.SAFETY_CLOSED:'Safety connected',
}


def command_packet(text, sequence):
    from .messages import DEFINITIONS
    parts=text.strip().split('|'); name=parts[0]; args=parts[1:]
    if name in _TOGGLES:
        if args: raise ValueError('unexpected arguments')
        mid,value=_TOGGLES[name]
        return pack(mid,value,sequence=sequence)
    for prop, label in ((1,'First'),(2,'Second')):
        for channel,sensor,short in ((0,'Thrust','Thr'),(1,'Torque','Trq')):
            for spelling,mid in ((f'cal{label}{sensor}',M.CALIBRATE),
                                 (f'set{label}{short}CalVal',M.SET_CALIBRATION),
                                 (f'set{label}{short}ArmLength',M.SET_ARM)):
                if name==spelling:
                    if len(args)!=1: raise ValueError('expected one value')
                    return pack(mid,prop,channel,float(args[0]),sequence=sequence)
    if name not in _SIMPLE: raise ValueError(f'unknown GUI command {name!r}')
    mid=_SIMPLE[name]; fmt=DEFINITIONS[mid][1][1:]
    if len(args)!=len(fmt): raise ValueError(f'{name}: expected {len(fmt)} arguments')
    values=[float(value) if kind=='f' else int(value) for value,kind in zip(args,fmt)]
    return pack(mid,*values,sequence=sequence)


def presentation_line(packet):
    """Produce a display/Qt-slot representation of already validated binary data."""
    mid=packet.message_id; values=unpack(packet)
    if mid==M.EVENT: return EVENT_TEXT.get(values[0])
    if mid==M.MEASUREMENTS: return 'Measurements: '+' '.join(map(str,values[1:]))
    if mid==M.LC_TEST: return 'LC test: '+' '.join(map(str,values[1:]))
    if mid==M.CAL_VALUE: return f'CalVal: {values[2]}'
    if mid==M.AOA_STATE: return 'readAoA|'+'|'.join(map(str,values))
    if mid==M.AOSS_STATE: return 'readAoSS|'+'|'.join(map(str,values))
    return None
