// pm4.hpp: Adreno A6xx (including Adreno 610 on Samsung Galaxy A05s) PM4 packet builder
// Derived from hakios-metal (https://github.com/oosexgang/hakios-metal)
#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

namespace a05s::metal::pm4 {

enum Opcode : uint8_t {
    kNop = 0x10,              // CP_NOP: padding and debug markers
    kWaitMemWrites = 0x12,    // CP_WAIT_MEM_WRITES: drain pending writes
    kWaitForMe = 0x13,        // CP_WAIT_FOR_ME: parser sync
    kWaitForIdle = 0x26,      // CP_WAIT_FOR_IDLE: GPU idle sync
    kMemWrite = 0x3d,         // CP_MEM_WRITE: 64-bit destination, payload
    kIndirectBuffer = 0x3f,   // CP_INDIRECT_BUFFER: call secondary buffer
    kMemToMem = 0x73,         // CP_MEM_TO_MEM: copy via CP
    kMemcpy = 0x75,           // CP_MEMCPY: hardware blit (A6xx+)
};

constexpr uint32_t oddParity(uint32_t v) {
    v ^= v >> 16;
    v ^= v >> 8;
    v ^= v >> 4;
    v &= 0xf;
    return (~0x6996u >> v) & 1u;
}

constexpr uint32_t kType4 = 0x40000000u;
constexpr uint32_t kType7 = 0x70000000u;
constexpr uint32_t kMaxType4Count = 0x7e;
constexpr uint32_t kMaxType7Count = 0x3fff;

constexpr uint32_t type4(uint32_t reg, uint32_t count) {
    return kType4 | count | (oddParity(count) << 7) | ((reg & 0x3ffffu) << 8) | (oddParity(reg) << 27);
}

constexpr uint32_t type7(uint32_t opcode, uint32_t count) {
    return kType7 | count | (oddParity(count) << 15) | ((opcode & 0x7fu) << 16) | (oddParity(opcode) << 23);
}

inline void pushNop(std::vector<uint32_t>& pkt, uint32_t payload = 0) {
    pkt.push_back(type7(kNop, 1));
    pkt.push_back(payload);
}

inline void pushMemcpy(std::vector<uint32_t>& pkt, uint64_t dst, uint64_t src, uint32_t words) {
    pkt.push_back(type7(kMemcpy, 5));
    pkt.push_back(words);
    pkt.push_back(static_cast<uint32_t>(src));
    pkt.push_back(static_cast<uint32_t>(src >> 32));
    pkt.push_back(static_cast<uint32_t>(dst));
    pkt.push_back(static_cast<uint32_t>(dst >> 32));
}

inline void pushWaitForIdle(std::vector<uint32_t>& pkt) {
    pkt.push_back(type7(kWaitForIdle, 0));
}

} // namespace a05s::metal::pm4
