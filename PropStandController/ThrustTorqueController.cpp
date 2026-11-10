#include "ThrustTorqueController.h"

static PinSet pinsFor(uint8_t prop) {
  if (prop == 0) {
    return PinSet{ THRUST_DAT_1_PIN, THRUST_CLK_1_PIN,
                   TORQUE_DAT_1_PIN, TORQUE_CLK_1_PIN };
  } else {
    return PinSet{ THRUST_DAT_2_PIN, THRUST_CLK_2_PIN,
                   TORQUE_DAT_2_PIN, TORQUE_CLK_2_PIN };
  }
}

ThrustTorqueController::ThrustTorqueController(uint8_t propellerId)
: _pins(pinsFor(propellerId)) {
  this->thrust = new HX711_ADC(_pins.thrDAT, _pins.thrSCK);
  this->torque = new HX711_ADC(_pins.trqDAT, _pins.trqSCK);
}

ThrustTorqueController::~ThrustTorqueController() {
  delete thrust;
  delete torque;
}

uint8_t ThrustTorqueController::begin(float thrustArmLength,
                                      float torqueArmLength,
                                      float thrustCalibration,
                                      float torqueCalibration) {
  this->init = false;
  thrustTimeout = torqueTimeout = false;
  // geometry must be valid
  if (thrustArmLength <= 0.0f || torqueArmLength <= 0.0f) return 1;

  // Always store arms first so status prints are truthful even if ADC init fails
  this->setThrustArmLength(thrustArmLength);
  this->setTorqueArmLength(torqueArmLength);

  // Safe cal factors (avoid div-by-zero)
  if (thrustCalibration != 0.0f) this->setThrustCalibration(thrustCalibration);
  else                           this->thrust->setCalFactor(this->thrust->getCalFactor() ? this->thrust->getCalFactor() : 1.0f);

  if (torqueCalibration != 0.0f) this->setTorqueCalibration(torqueCalibration);
  else                           this->torque->setCalFactor(this->torque->getCalFactor() ? this->torque->getCalFactor() : 1.0f);

  this->thrust->begin();
  this->torque->begin();

  // HX711_ADC 1.2.12 startMultiple() has a function-static tare deadline:
  // a second stand started later inherits the first stand's expired timeout.
  // Its startStatus also survives begin(), skipping tare on reconfiguration.
  // Own the elapsed-time budget and explicitly start a fresh tare on every INIT.
  const uint32_t started = millis();
  while (uint32_t(millis() - started) < STABILIZATION_TIME) {
    this->thrust->update();
    this->torque->update();
    yield();
  }

  this->thrust->tareNoDelay();
  this->torque->tareNoDelay();
  bool thrustReady = false, torqueReady = false;
  while (uint32_t(millis() - started) < SENSOR_STARTUP_TIMEOUT_MS) {
    if (!thrustReady) thrustReady = this->thrust->update() == 2;
    if (!torqueReady) torqueReady = this->torque->update() == 2;
    if (thrustReady && torqueReady) break;
    yield();
  }

  thrustTimeout = !thrustReady;
  torqueTimeout = !torqueReady;
  // Reaching the outer deadline must never be mistaken for successful startup.
  if (thrustTimeout || torqueTimeout) return thrustTimeout ? 2 : 3;

  this->init = true;
  return 0;
}

float ThrustTorqueController::calibrateThrust(float knownMass) {
  this->thrust->refreshDataSet();
  float cal = this->thrust->getNewCalibration(knownMass);
  this->thrustCalibrated = true;
  return cal;
}

float ThrustTorqueController::calibrateTorque(float knownMass) {
  this->torque->refreshDataSet();
  float cal = this->torque->getNewCalibration(knownMass);
  this->torqueCalibrated = true;
  return cal;
}

void ThrustTorqueController::setThrustCalibration(float value) {
  this->thrust->setCalFactor(value);
  this->thrustCalibrated = true;
}
void ThrustTorqueController::setTorqueCalibration(float value) {
  this->torque->setCalFactor(value);
  this->torqueCalibrated = true;
}
void ThrustTorqueController::setThrustArmLength(float value) {
  this->thrustArmLength = value;
}
void ThrustTorqueController::setTorqueArmLength(float value) {
  this->torqueArmLength = value;
}
void ThrustTorqueController::tareAll() {
  this->thrust->tare();
  thrustTimeout = this->thrust->getTareTimeoutFlag();
  this->torque->tare();
  torqueTimeout = this->torque->getTareTimeoutFlag();
}

float ThrustTorqueController::getThrustArmLength() const {
  return this->thrustArmLength;
}

float ThrustTorqueController::getTorqueArmLength() const {
  return this->torqueArmLength;
}

float ThrustTorqueController::getThrustCalibration() const {
  return this->thrust ? this->thrust->getCalFactor() : 0.0f;
}

float ThrustTorqueController::getTorqueCalibration() const {
  return this->torque ? this->torque->getCalFactor() : 0.0f;
}

void ThrustTorqueController::getThrust(float* data) {
  data[0] = updateThrust();                                // g
  data[1] = (data[0] * G) / this->thrustArmLength; // mN (mass in g; dimensionless thrust ratio)
}
void ThrustTorqueController::getTorque(float* data) {
  data[0] = updateTorque();                                // g
  data[1] = data[0] * G * (this->torqueArmLength / 1000.0f); // N·mm (mass in g)
}
/*float ThrustTorqueController::updateThrust() {
  this->thrust->update();
  return this->thrust->getData();
}
float ThrustTorqueController::updateTorque() {
  this->torque->update();
  return this->torque->getData();
}*/

float ThrustTorqueController::updateThrust() {
  if (this->thrust->dataWaitingAsync()) {
    this->thrust->updateAsync();
  }
  return this->thrust->getData();
}

float ThrustTorqueController::updateTorque() {
  if (this->torque->dataWaitingAsync()) {
    this->torque->updateAsync();
  }
  return this->torque->getData();
} //Crismar

bool ThrustTorqueController::getInit() { return this->init; }
bool ThrustTorqueController::getThrustCalibrated() { return this->thrustCalibrated; }
bool ThrustTorqueController::getTorqueCalibrated() { return this->torqueCalibrated; }
bool ThrustTorqueController::getCalibrated() { return this->thrustCalibrated && this->torqueCalibrated; }
