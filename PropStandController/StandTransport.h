#ifndef STAND_TRANSPORT_H
#define STAND_TRANSPORT_H
#include <Arduino.h>
#include "StandMessages.h"
namespace standlink {
enum Result : uint8_t { ACCEPTED=0, INVALID=1, BAD_STATE=2, UNSUPPORTED=3, BUSY=4, FAILED=5, TIMEOUT=6 };
enum EventCode : uint8_t { READY=0, HOMED=1, JOG_DONE=2, CENTER_DONE=3, TARE_DONE=4,
  LIMIT_SWITCH=5, AXIS_LIMIT=6, EMERGENCY=7, EMERGENCY_CLEARED=8, SAFETY_OPEN=9,
  SAFETY_CLOSED=10, MOVE_DONE=11, MOVE_TIMEOUT=12 };

// Arduino adapter. Core codec and generated messages do not depend on Arduino.
class Transport {
 public:
  explicit Transport(Stream& stream) : decoder(messageSpec), stream_(stream) {}
  Decoder decoder;
  SequenceTracker rxSequence;
  uint32_t txErrors=0;
  bool enabled=false;
  bool send(Packet packet) {
    if (!enabled) return false;
    uint8_t extra=0; int16_t size=messageSpec(packet.id,extra);
    if (size==-2 || (size>=0 && size!=packet.length)) return false;
    packet.sequence=txSequence_++; packet.system=1;
    uint8_t frame[MAX_FRAME]; size_t count=encode(packet,extra,frame,sizeof(frame));
    // A failed/short write consumes its SEQ and is never silently retried.
    if (stream_.write(frame,count)!=count) { ++txErrors; return false; }
    return true;
  }
  template<typename T> bool send(const T& value) { return send(pack(value)); }
  bool receive(Packet& packet) {
    decoder.expire(millis());
    if (decoder.next(packet)) return true;
    unsigned budget=MAX_FRAME;
    while (budget-- && stream_.available()>0) {
      int c=stream_.read();
      if (c>=0 && decoder.push(uint8_t(c),millis(),packet)) return true;
    }
    return false;
  }
 private:
  Stream& stream_;
  uint8_t txSequence_=0;
};

// Existing diagnostic print calls are collected into bounded STATUS_TEXT packets.
// This sink cannot create events or data frames from the content of a string.
class DiagnosticPrint : public Print {
 public:
  explicit DiagnosticPrint(Transport& transport) : transport_(transport) {}
  using Print::write;
  size_t write(uint8_t c) override {
    if (c=='\r') return 1;
    if (c=='\n') { flushLine(); return 1; }
    packet_.payload[packet_.length++]=c;
    if (packet_.length==MAX_PAYLOAD) flushLine();
    return 1;
  }
  void flushLine() {
    if (packet_.length) { packet_.id=STATUS_TEXT; transport_.send(packet_); packet_.length=0; }
  }
 private:
  Transport& transport_;
  Packet packet_;
};
}
#endif
