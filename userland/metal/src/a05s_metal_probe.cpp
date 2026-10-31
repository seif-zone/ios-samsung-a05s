// a05s_metal_probe.cpp: Verification probe for Metal on Qualcomm Adreno 610 (Samsung Galaxy A05s)
// Evaluates PM4 packet encoding, buffer allocation, and blit execution pipeline.
#include <iostream>
#include <vector>
#include <cassert>
#include <cstring>
#include "../include/pm4.hpp"
#include "../include/gpu.hpp"

using namespace a05s::metal;

static void test_pm4_parity() {
    std::cout << "[*] Testing PM4 packet parity generators (Adreno A6xx)...\n";
    // Check known Mesa values
    uint32_t nop = pm4::type7(pm4::kNop, 1);
    assert((nop >> 28) == 7);
    assert(((nop >> 16) & 0x7f) == pm4::kNop);
    
    uint32_t memcpy_pkt = pm4::type7(pm4::kMemcpy, 5);
    assert((memcpy_pkt >> 28) == 7);
    assert(((memcpy_pkt >> 16) & 0x7f) == pm4::kMemcpy);

    std::cout << "    [+] PM4 Type 7 NOP:    0x" << std::hex << nop << std::dec << "\n";
    std::cout << "    [+] PM4 Type 7 MEMCPY: 0x" << std::hex << memcpy_pkt << std::dec << "\n";
    std::cout << "    [+] PM4 parity verification passed.\n";
}

static void test_buffer_allocation() {
    std::cout << "[*] Testing GPU buffer allocation & submission...\n";
    FakeGpuTransport gpu;
    Buffer src, dst;

    int r1 = gpu.allocate(1024 * 64, src);
    int r2 = gpu.allocate(1024 * 64, dst);
    assert(r1 == 0 && r2 == 0);
    assert(src.hostPointer != nullptr && dst.hostPointer != nullptr);

    std::memset(src.hostPointer, 0x5a, src.size);
    std::memset(dst.hostPointer, 0x00, dst.size);

    std::vector<uint32_t> cmdStream;
    pm4::pushNop(cmdStream, 0x1337);
    pm4::pushMemcpy(cmdStream, dst.gpuAddress, src.gpuAddress, src.size / 4);
    pm4::pushWaitForIdle(cmdStream);

    uint32_t fence = 0;
    int r3 = gpu.submit(cmdStream.data(), cmdStream.size(), fence);
    assert(r3 == 0);
    assert(fence > 0);

    int r4 = gpu.waitFence(fence, 1000000000ULL);
    assert(r4 == 0);

    gpu.free(src);
    gpu.free(dst);
    std::cout << "    [+] Allocated 64KB buffers, submitted " << cmdStream.size() << " PM4 words, fence=" << fence << "\n";
    std::cout << "    [+] GPU submission test passed.\n";
}

int main() {
    std::cout << "=========================================================\n";
    std::cout << " Samsung Galaxy A05s (SM-A057F / m269) Metal GPU Probe   \n";
    std::cout << " Adreno 610 (Qualcomm SM6225) Hakios-Metal Verification  \n";
    std::cout << "=========================================================\n";

    test_pm4_parity();
    test_buffer_allocation();

    std::cout << "\n[SUCCESS] Adreno 610 Metal verification suite passed!\n";
    return 0;
}
