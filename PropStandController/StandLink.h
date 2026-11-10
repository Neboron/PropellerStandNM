#ifndef STAND_LINK_H
#define STAND_LINK_H
// Standalone C++11 framing, deliberately independent of Arduino and struct ABI.
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <limits>
namespace standlink {
constexpr uint8_t STX = 0x42;
constexpr size_t MAX_PAYLOAD = 255;
constexpr size_t MAX_FRAME = 262;
inline uint16_t crc16(const uint8_t* data, size_t n, uint16_t crc = 0xffff) {
  while (n--) {
    crc ^= *data++;
    for (uint8_t bit=0; bit<8; ++bit) crc = (crc >> 1) ^ ((crc & 1) ? 0x8408 : 0);
  }
  return crc;
}
struct Packet {
  uint8_t sequence=0, system=1, id=0, length=0;
  uint8_t payload[MAX_PAYLOAD] = {};
};
inline size_t encode(const Packet& p, uint8_t extra, uint8_t* out, size_t capacity) {
  const size_t n = size_t(p.length) + 7;
  if (capacity < n) return 0;
  out[0]=STX; out[1]=p.length; out[2]=p.sequence; out[3]=p.system; out[4]=p.id;
  memcpy(out+5, p.payload, p.length);
  uint16_t crc=crc16(out+1, p.length+4); crc=crc16(&extra, 1, crc);
  out[n-2]=uint8_t(crc); out[n-1]=uint8_t(crc >> 8);
  return n;
}
// Spec returns -2 unknown, -1 variable length, or an exact payload length.
using Spec = int16_t (*)(uint8_t, uint8_t&);
class Decoder {
 public:
  explicit Decoder(Spec spec, uint8_t system=1, uint32_t timeout=500)
      : spec_(spec), system_(system), timeout_(timeout) {}
  uint32_t crcErrors=0, discardedBytes=0, timeouts=0;
  bool push(uint8_t byte, uint32_t now, Packet& out) {
    expire(now);
    if (used_ == MAX_FRAME) drop(1); // defensive bound
    buffer_[used_++]=byte; lastByte_=now;
    return next(out);
  }
  bool next(Packet& out) {
    while (used_) {
      if (buffer_[0] != STX) { drop(1); continue; }
      size_t total=0;
      int state=candidate(0,total);
      if (state==0) {
        if (!recoveryBytes_) return false;
        drop(1); continue;
      }
      if (state != 1) { if (state==-2) ++crcErrors; drop(1); continue; }
      out.length=buffer_[1]; out.sequence=buffer_[2]; out.system=buffer_[3]; out.id=buffer_[4];
      memcpy(out.payload,buffer_+5,out.length);
      remove(total);
      return true;
    }
    return false;
  }
  void expire(uint32_t now) {
    if (used_ && !recoveryBytes_ && uint32_t(now-lastByte_)>=timeout_) { ++timeouts; drop(1); recoveryBytes_=used_; }
  }
  size_t buffered() const { return used_; }
 private:
  int candidate(size_t offset, size_t& total) const {
    if (used_-offset < 5) return 0;
    uint8_t extra=0, length=buffer_[offset+1];
    int16_t expected=spec_(buffer_[offset+4],extra);
    if (buffer_[offset+3]!=system_ || expected==-2 || (expected>=0 && expected!=length)) return -1;
    total=size_t(length)+7;
    if (used_-offset<total) return 0;
    uint16_t crc=crc16(buffer_+offset+1,length+4); crc=crc16(&extra,1,crc);
    uint16_t actual=uint16_t(buffer_[offset+total-2]) | uint16_t(buffer_[offset+total-1])<<8;
    return crc==actual ? 1 : -2;
  }
  void remove(size_t n) { memmove(buffer_,buffer_+n,used_-n); used_-=n; recoveryBytes_=n>=recoveryBytes_?0:recoveryBytes_-n; }
  void drop(size_t n) { discardedBytes+=n; remove(n); }
  Spec spec_;
  uint8_t system_;
  uint32_t timeout_, lastByte_=0;
  size_t recoveryBytes_=0;
  size_t used_=0;
  uint8_t buffer_[MAX_FRAME]={};
};
class SequenceTracker {
 public:
  uint32_t gaps=0, duplicates=0;
  bool observe(const Packet& p) {
    if (have_ && p.sequence==last_.sequence && p.id==last_.id && p.system==last_.system &&
        p.length==last_.length && memcmp(p.payload,last_.payload,p.length)==0) { ++duplicates; return false; }
    if (have_) {
      uint8_t delta=uint8_t(p.sequence-last_.sequence);
      if (delta!=1) gaps+=uint8_t(delta-1);
    }
    last_=p; have_=true; return true;
  }
  void reset() { have_=false; }
 private:
  bool have_=false;
  Packet last_;
};
inline void putU8(uint8_t*& p,uint8_t v) { *p++=v; }
inline void putU16(uint8_t*& p,uint16_t v) { putU8(p,uint8_t(v)); putU8(p,uint8_t(v>>8)); }
inline void putU32(uint8_t*& p,uint32_t v) { putU16(p,uint16_t(v)); putU16(p,uint16_t(v>>16)); }
inline uint8_t getU8(const uint8_t*& p) { return *p++; }
inline uint16_t getU16(const uint8_t*& p) { uint16_t v=getU8(p); return v | uint16_t(getU8(p))<<8; }
inline uint32_t getU32(const uint8_t*& p) { uint32_t v=getU16(p); return v | uint32_t(getU16(p))<<16; }
inline void putI8(uint8_t*& p,int8_t v) { putU8(p,uint8_t(v)); }
inline void putI32(uint8_t*& p,int32_t v) { putU32(p,uint32_t(v)); }
inline int8_t getI8(const uint8_t*& p) { uint8_t v=getU8(p); int8_t r; memcpy(&r,&v,1); return r; }
inline int32_t getI32(const uint8_t*& p) { uint32_t v=getU32(p); int32_t r; memcpy(&r,&v,4); return r; }
static_assert(sizeof(float)==4 && std::numeric_limits<float>::is_iec559, "IEEE754 binary32 required");
inline void putF32(uint8_t*& p,float v) { uint32_t bits; memcpy(&bits,&v,4); putU32(p,bits); }
inline float getF32(const uint8_t*& p) { uint32_t bits=getU32(p); float v; memcpy(&v,&bits,4); return v; }
} // namespace standlink
#endif
