#ifndef STAND_COMMANDS_H
#define STAND_COMMANDS_H
// Hardware application boundary. Included after controller declarations in the sketch.
// All incoming payloads have passed framing/CRC; typed unpack also validates length
// and finite floating-point values before any side effect.
static bool protocolReady=false;
static uint8_t axisRequestId=0, axisRequestSeq=0;
static uint32_t axisStarted=0, axisLastPoll=0;
static bool axisLimitsSet=false;
static int32_t configuredMaxX=0, configuredMaxY=0;
static uint32_t configuredSpeedX=0, configuredSpeedY=0;
static bool axisBusy() { return axisRequestId!=0; }

static bool sendStepperCommand(const String& command) {
  // Keep the existing separate I2C board protocol within its 32-byte Wire buffer.
  if (command.length()>32) return false;
  Wire.beginTransmission(stepper_address);
  Wire.write(command.c_str(),command.length());
  return Wire.endTransmission()==0;
}
static String axisCommand(char name,int32_t x,int32_t y,uint32_t sx,uint32_t sy) {
  return String(name)+"|"+String(x)+"|"+String(y)+"|"+String(sx)+"|"+String(sy);
}
static void startAxisRequest(const standlink::Packet& p) {
  axisRequestId=p.id; axisRequestSeq=p.sequence; axisStarted=millis();
}
static bool safeToMove() { return !emergency_state && !no_safety; }

static standlink::Result dispatchCommand(const standlink::Packet& p) {
  using namespace standlink;
  checkEmergency(); // Refresh hardware interlocks before processing a command.
  if (p.id==STOP) {
    escHardStopBoth();
    return ACCEPTED;
  }
  if (!protocolReady) return BAD_STATE;
  if (p.id==INIT) {
    if (axisBusy() || escEnabled1 || escEnabled2) return BUSY;
    Init v; if (!unpack(p,v)) return INVALID;
    if ((v.prop_count!=1 && v.prop_count!=2) || v.trq_arm1_mm<=0 || v.thrust_ratio1<=0 ||
        v.trq_cal1==0 || v.thr_cal1==0 || (v.prop_count==2 &&
        (v.trq_arm2_mm<=0 || v.thrust_ratio2<=0 || v.trq_cal2==0 || v.thr_cal2==0))) return INVALID;
    InitParams params;
    params.fTrqArm=v.trq_arm1_mm; params.fThrArm=v.thrust_ratio1;
    params.fTrqCal=v.trq_cal1; params.fThrCal=v.thr_cal1;
    params.sTrqArm=v.trq_arm2_mm; params.sThrArm=v.thrust_ratio2;
    params.sTrqCal=v.trq_cal2; params.sThrCal=v.thr_cal2; params.tSetup=v.prop_count;
    input_complete=false;
    cal_found=false; tare_done=false;
    read_stream_test=false; measure_in_progress=false;
    if (!initControllersFrom(params)) return FAILED;
    input_complete=true; cal_found=true;
    sendProtocolEvent(READY,p.sequence,p.id);
    return ACCEPTED;
  }
  if (p.id==BEACON) {
    Beacon v; if (!unpack(p,v) || v.enabled>1) return INVALID;
    if (v.enabled && !safeToMove()) return BAD_STATE;
    beacon_on=v.enabled; return ACCEPTED;
  }
  if (p.id==TEST_STREAM) {
    TestStream v; if (!unpack(p,v) || v.enabled>1) return INVALID;
    // OFF is harmless before INIT and is sent when the GUI receives safety state.
    if (v.enabled && !input_complete) return BAD_STATE;
    read_stream_test=v.enabled; return ACCEPTED;
  }
  if (!input_complete) return BAD_STATE;
  // Reconfiguration/calibration while axes are moving is rejected, not queued.
  if (axisBusy() && p.id!=TEST_STREAM && p.id!=PITOT_READ && p.id!=AOA_READ &&
      p.id!=AOSS_READ && p.id!=STATUS && p.id!=AOSS_CONFIG_GET) return BUSY;
  switch (p.id) {
    case AXIS_LIMITS: {
      AxisLimits v; if (!unpack(p,v) || v.max_x<=0 || v.max_y<=0 || !v.speed_x || !v.speed_y ||
          !v.accel_x || !v.accel_y || v.speed_x>32767 || v.speed_y>32767 || v.accel_x>32767 || v.accel_y>32767) return INVALID;
      String cmd=String("l|")+String(v.max_x)+"|"+String(v.max_y)+"|"+String(v.speed_x)+"|"+
        String(v.speed_y)+"|"+String(v.accel_x)+"|"+String(v.accel_y);
      if (!sendStepperCommand(cmd)) return FAILED;
      configuredMaxX=v.max_x; configuredMaxY=v.max_y; configuredSpeedX=v.speed_x; configuredSpeedY=v.speed_y; axisLimitsSet=true; return ACCEPTED;
    }
    case HOME:
      if (!safeToMove() || !axisLimitsSet) return BAD_STATE;
      if (!sendStepperCommand("home")) return FAILED;
      homing_done=false; startAxisRequest(p); return ACCEPTED;
    case CENTER:
      if (!safeToMove() || !homing_done) return BAD_STATE;
      if (!sendStepperCommand("center")) return FAILED;
      startAxisRequest(p); return ACCEPTED;
    case JOG:
    case MEASURE_MOVE: {
      int32_t x,y; uint32_t sx,sy;
      if (p.id==JOG) {
        Jog v; if (!unpack(p,v)) return INVALID;
        x=v.x; y=v.y; sx=v.speed_x; sy=v.speed_y;
      } else {
        MeasureMove v; if (!unpack(p,v)) return INVALID;
        x=v.x; y=v.y; sx=v.speed_x; sy=v.speed_y;
      }
      if (!safeToMove() || !homing_done || !axisLimitsSet) return BAD_STATE;
      if (x<0 || y<0 || x>configuredMaxX || y>configuredMaxY || !sx || !sy || sx>configuredSpeedX || sy>configuredSpeedY) return INVALID;
      if (!sendStepperCommand(axisCommand(p.id==JOG?'j':'m',x,y,sx,sy))) return FAILED;
      startAxisRequest(p);
      if (p.id==MEASURE_MOVE) { reqX=x; reqY=y; measure_in_progress=true; }
      return ACCEPTED;
    }
    case TARE:
      if (escEnabled1 || escEnabled2) return BAD_STATE;
      thrustTorqueControllers[0]->tareAll();
      if (twoProps) thrustTorqueControllers[1]->tareAll();
      if (thrustTorqueControllers[0]->thrustTareTimeout() || thrustTorqueControllers[0]->torqueTareTimeout() ||
          (twoProps && (thrustTorqueControllers[1]->thrustTareTimeout() || thrustTorqueControllers[1]->torqueTareTimeout()))) return FAILED;
      tare_done=true; sendProtocolEvent(TARE_DONE,p.sequence,p.id); return ACCEPTED;
    case START_MOTORS: {
      StartMotors v; if (!unpack(p,v) || v.pwm1_us<500 || v.pwm1_us>2500 || v.pwm2_us<500 || v.pwm2_us>2500) return INVALID;
      if (!safeToMove()) return BAD_STATE;
      escEnabled1=true; escTarget1=constrain(v.pwm1_us,escMinUs1,escMaxUs1);
      if (twoProps && thrustTorqueControllers[1]) { escEnabled2=true; escTarget2=constrain(v.pwm2_us,escMinUs2,escMaxUs2); }
      return ACCEPTED;
    }
    case SET_MIN:
    case SET_MAX: {
      uint8_t motor; uint16_t value;
      if (p.id==SET_MIN) { SetMin v; if (!unpack(p,v)) return INVALID; motor=v.motor; value=v.pwm_us; }
      else { SetMax v; if (!unpack(p,v)) return INVALID; motor=v.motor; value=v.pwm_us; }
      if ((motor!=1 && motor!=2) || value<500 || value>2500) return INVALID;
      if (escEnabled1 || escEnabled2) return BAD_STATE;
      volatile int& mn=motor==1?escMinUs1:escMinUs2;
      volatile int& mx=motor==1?escMaxUs1:escMaxUs2;
      if (p.id==SET_MIN) { if (value>mx) return INVALID; mn=value; }
      else { if (value<mn) return INVALID; mx=value; }
      return ACCEPTED;
    }
    case SET_RAMP: {
      SetRamp v; if (!unpack(p,v) || v.milliseconds<50 || v.milliseconds>10000) return INVALID;
      escRampMs=v.milliseconds; return ACCEPTED;
    }
    case TEST_FIRST:
    case TEST_SECOND: {
      uint16_t pwm;
      if (p.id==TEST_FIRST) { TestFirst v; if (!unpack(p,v)) return INVALID; pwm=v.pwm_us; }
      else { TestSecond v; if (!unpack(p,v)) return INVALID; pwm=v.pwm_us; }
      if (pwm<500 || pwm>2500) return INVALID;
      if (!safeToMove() || (p.id==TEST_SECOND && !twoProps)) return BAD_STATE;
      if (p.id==TEST_FIRST) { escEnabled1=true; escTarget1=escCurrent1=constrain(pwm,escMinUs1,escMaxUs1); }
      else { escEnabled2=true; escTarget2=escCurrent2=constrain(pwm,escMinUs2,escMaxUs2); }
      return ACCEPTED;
    }
    case PROPS: {
      Props v; if (!unpack(p,v) || (v.count!=1 && v.count!=2)) return INVALID;
      if (escEnabled1 || escEnabled2) return BAD_STATE;
      if (v.count==1) disableSecondProp();
      else { enableSecondProp(); if (!twoProps) return FAILED; }
      return ACCEPTED;
    }
    case STATUS:
      for (int i=0;i<(twoProps?2:1);++i) {
        protocolLog.print("PROP "); protocolLog.println(i+1);
        protocolLog.print("  ThrRatio="); protocolLog.println(thrustTorqueControllers[i]->getThrustArmLength(),6);
        protocolLog.print("  TrqArm_mm="); protocolLog.println(thrustTorqueControllers[i]->getTorqueArmLength(),6);
        protocolLog.print("  ThrCF="); protocolLog.println(thrustTorqueControllers[i]->getThrustCalibration(),6);
        protocolLog.print("  TrqCF="); protocolLog.println(thrustTorqueControllers[i]->getTorqueCalibration(),6);
      }
      return ACCEPTED;
    case CALIBRATE:
    case SET_CALIBRATION:
    case SET_ARM: {
      uint8_t prop,channel; float value;
      if (p.id==CALIBRATE) { Calibrate v; if (!unpack(p,v)) return INVALID; prop=v.prop; channel=v.channel; value=v.mass_g; }
      else if (p.id==SET_CALIBRATION) { SetCalibration v; if (!unpack(p,v)) return INVALID; prop=v.prop; channel=v.channel; value=v.factor; }
      else { SetArm v; if (!unpack(p,v)) return INVALID; prop=v.prop; channel=v.channel; value=v.value; }
      if ((prop!=1 && prop!=2) || channel>1 || value==0) return INVALID;
      if ((p.id==CALIBRATE || (p.id==SET_ARM && channel==1)) && value<=0) return INVALID;
      if (escEnabled1 || escEnabled2 || (prop==2 && !twoProps)) return BAD_STATE;
      ThrustTorqueController* sensor=thrustTorqueControllers[prop-1];
      if (!sensor) return BAD_STATE;
      if (p.id==CALIBRATE) {
        float factor=channel==0?sensor->calibrateThrust(value):sensor->calibrateTorque(value);
        if (!isfinite(factor) || factor==0) return FAILED;
        standLink.send(CalValue{p.sequence,p.id,factor}); cal_found=true;
      } else if (p.id==SET_CALIBRATION) {
        if (channel==0) sensor->setThrustCalibration(value); else sensor->setTorqueCalibration(value);
      } else {
        if (channel==0) sensor->setThrustArmLength(value); else sensor->setTorqueArmLength(value);
      }
      // Cache actual values for later props reconfiguration.
      if (prop==1) {
        firstThrCalVal=sensor->getThrustCalibration(); firstTrqCalVal=sensor->getTorqueCalibration();
        firstThrArmLength=sensor->getThrustArmLength(); firstTrqArmLength=sensor->getTorqueArmLength();
      } else {
        secondThrCalVal=sensor->getThrustCalibration(); secondTrqCalVal=sensor->getTorqueCalibration();
        secondThrArmLength=sensor->getThrustArmLength(); secondTrqArmLength=sensor->getTorqueArmLength();
      }
      return ACCEPTED;
    }
    case AOA_TRIM: {
      AoaTrim v; if (!unpack(p,v) || v.degrees < -180 || v.degrees > 180) return INVALID;
      if (!safeToMove()) return BAD_STATE;
      trimAoA=v.degrees; aoaSensorPhysicalAngle=aoaTargetPhysicalDegForAxisState();
      aoaCanCommandServoDeg(aoaSensorPhysicalAngle); return ACCEPTED;
    }
    case AOA_LIMIT: {
      AoaLimit v; if (!unpack(p,v) || v.degrees>180) return INVALID;
      limAoA=v.degrees; return ACCEPTED;
    }
    case AOA_ENABLE: {
      AoaEnable v; if (!unpack(p,v) || v.enabled>1) return INVALID;
      if (v.enabled && !safeToMove()) return BAD_STATE;
      setAoAAxisEnabled(v.enabled); return ACCEPTED;
    }
    case AOA_READ: {
      uint16_t pos=0;
      if (!hitecReadReg16(AOA_CAN_ARB_ID,AOA_CAN_SERVO_ID,REG_POSITION,pos,50)) return FAILED;
      float physical=servoCountsToPhysicalDeg(pos);
      standLink.send(AoaState{pos,physical,wrapSignedDeg(physical-trimAoA)}); return ACCEPTED;
    }
    case AOSS_TRIM: {
      AossTrim v; if (!unpack(p,v)) return INVALID;
      aossTrimDeg=v.degrees; return ACCEPTED;
    }
    case AOSS_MOVE:
    case AOSS_SERVO_MOVE: {
      float target;
      if (p.id==AOSS_MOVE) { AossMove v; if (!unpack(p,v)) return INVALID; target=v.degrees; }
      else { AossServoMove v; if (!unpack(p,v)) return INVALID; target=aossTubeDegFromServoDeg(v.degrees); }
      if (!safeToMove()) return BAD_STATE;
      target=clampf(target,aossMinTubeDeg,aossMaxTubeDeg);
      aossCanCommandServoRelDeg(target); aossSensorRelAngle=target; return ACCEPTED;
    }
    case AOSS_RATIO: {
      AossRatio v; if (!unpack(p,v) || v.ratio<0.01f || v.ratio>1000) return INVALID;
      if (!safeToMove()) return BAD_STATE;
      AoSSratio=v.ratio; aossCanCommandServoRelDeg(aossSensorRelAngle); return ACCEPTED;
    }
    case AOSS_LIMITS: {
      AossLimits v; if (!unpack(p,v) || v.min_deg < -90 || v.max_deg > 90 || v.min_deg>v.max_deg) return INVALID;
      if (!safeToMove()) return BAD_STATE;
      aossMinTubeDeg=v.min_deg; aossMaxTubeDeg=v.max_deg;
      aossSensorRelAngle=clampf(aossSensorRelAngle,aossMinTubeDeg,aossMaxTubeDeg);
      aossCanCommandServoRelDeg(aossSensorRelAngle); return ACCEPTED;
    }
    case AOSS_ENABLE: {
      AossEnable v; if (!unpack(p,v) || v.enabled>1) return INVALID;
      if (v.enabled && !safeToMove()) return BAD_STATE;
      aoss_enabled=v.enabled; return ACCEPTED;
    }
    case AOSS_READ:
      aossCanReadbackUpdate();
      standLink.send(AossState{aossServoPosNow,int32_t(aossTurnNow),aossServoDegNow,aossTubeDegNow}); return ACCEPTED;
    case AOSS_ZERO:
      aossCanReadbackUpdate(); aossZeroOffsetDeg=aossServoDegNow; aossSensorRelAngle=0; return ACCEPTED;
    case AOSS_DIRECTION: {
      AossDirection v; if (!unpack(p,v) || (v.direction!=-1 && v.direction!=1)) return INVALID;
      aossDir=v.direction; return ACCEPTED;
    }
    case AOSS_CAL: {
      AossCal v; if (!unpack(p,v)) return INVALID;
      aossCanReadbackUpdate(); aossZeroOffsetDeg=aossServoDegNow-float(aossDir)*v.degrees; return ACCEPTED;
    }
    case AOSS_TEST:
      if (!safeToMove()) return BAD_STATE;
      aossCanCommandServoRelDeg(-10); delay(500); aossCanCommandServoRelDeg(0); return ACCEPTED;
    case AOSS_TURN_SETUP:
      if (!safeToMove()) return BAD_STATE;
      aossEnableTurnModeAndReset(); aossPrintRunMode(); return ACCEPTED;
    case AOSS_CONFIG_GET:
      standLink.send(AossConfig{AoSSratio,aossMinTubeDeg,aossMaxTubeDeg}); return ACCEPTED;
    case PITOT_READ:
      printPitotLive("read"); return ACCEPTED;
    case PITOT_STREAM: {
      PitotStream v; if (!unpack(p,v) || v.enabled>1) return INVALID;
      pitot_live_stream=v.enabled; pitot_live_mode=v.enabled; return ACCEPTED;
    }
    case PITOT_HOLD: {
      PitotHold v; if (!unpack(p,v) || v.enabled>1) return INVALID;
      pitot_live_mode=v.enabled; return ACCEPTED;
    }
    case RAW_PITOT_STREAM: {
      RawPitotStream v; if (!unpack(p,v) || v.enabled>1) return INVALID;
      read_stream=v.enabled; return ACCEPTED;
    }
    default: return UNSUPPORTED;
  }
}

void manageCommands() {
  using namespace standlink;
  Packet p;
  // At most four commands per scheduler pass; no blocking serial read.
  for (unsigned count=0; count<4 && standLink.receive(p); ++count) {
    if (p.id==HELLO) {
      Hello hello;
      bool match=unpack(p,hello) && hello.version==VERSION && hello.schema_hash==SCHEMA_HASH;
      protocolReady=match;
      if (match) standLink.rxSequence.reset(); // explicit new host session
      standLink.rxSequence.observe(p);
      standLink.send(HelloReply{VERSION,SCHEMA_HASH,millis()});
      if (match) {
        sendProtocolEvent(emergency_state?EMERGENCY:EMERGENCY_CLEARED);
        sendProtocolEvent(no_safety?SAFETY_OPEN:SAFETY_CLOSED);
      }
      continue;
    }
    bool fresh=standLink.rxSequence.observe(p);
    if (!isCommand(p.id)) continue; // never act on echoed device telemetry
    // Never execute an immediately duplicated command twice. Re-send its result.
    static Ack lastAck={0,0,UNSUPPORTED};
    if (!fresh) {
      if (lastAck.request_seq==p.sequence && lastAck.request_id==p.id) standLink.send(lastAck);
      continue;
    }
    Result result=dispatchCommand(p);
    lastAck=Ack{p.sequence,p.id,uint8_t(result)};
    standLink.send(lastAck);
  }
}

void serviceAxisOperation() {
  using namespace standlink;
  if (!axisBusy()) return;
  if (!safeToMove()) { axisRequestId=0; measure_in_progress=false; return; }
  if (uint32_t(millis()-axisStarted)>=TIMEOUT_MS) {
    measure_in_progress=false;
    sendProtocolEvent(MOVE_TIMEOUT,axisRequestSeq,axisRequestId);
    axisRequestId=0; homing_done=false;
    escHardStopBoth(); // No claim that independent steppers have stopped.
    return;
  }
  if (axisRequestId==MEASURE_MOVE || uint32_t(millis()-axisLastPoll)<20) return;
  axisLastPoll=millis();
  Wire.requestFrom(stepper_address,1);
  if (!Wire.available()) return;
  uint8_t state=Wire.read(), event=255;
  if (state==1 && axisRequestId==HOME) { homing_done=true; event=HOMED; }
  else if (state==2 && axisRequestId==JOG) event=JOG_DONE;
  else if (state==5 && axisRequestId==CENTER) event=CENTER_DONE;
  else if (state==3) event=AXIS_LIMIT;
  else if (state==4) { homing_done=false; event=LIMIT_SWITCH; }
  if (event!=255) { sendProtocolEvent(event,axisRequestSeq,axisRequestId); axisRequestId=0; }
}

void sendHeartbeat() {
  static uint32_t last=0;
  if (uint32_t(millis()-last)<1000) return;
  last=millis();
  uint16_t flags=(input_complete?1:0)|(homing_done?2:0)|(emergency_state?4:0)|(no_safety?8:0)|(axisBusy()?16:0);
  standLink.send(standlink::Heartbeat{millis(),flags,standLink.decoder.crcErrors,
    standLink.rxSequence.gaps,standLink.rxSequence.duplicates,standLink.txErrors});
}
#endif
