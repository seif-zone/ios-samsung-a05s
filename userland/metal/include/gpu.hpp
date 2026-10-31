// gpu.hpp: Adreno GPU Memory & Hardware Submission Abstraction
// Supports both simulated fake GPU testing and real MSM DRM ioctl / IOKit transport
#pragma once

#include <cstdint>
#include <cstddef>
#include <vector>
#include <memory>
#include <string>

namespace a05s::metal {

struct Buffer {
    uint32_t handle = 0;
    uint64_t gpuAddress = 0;
    size_t size = 0;
    void* hostPointer = nullptr;
};

class Transport {
public:
    virtual ~Transport() = default;
    virtual int allocate(size_t size, Buffer& outBuffer) = 0;
    virtual int free(Buffer& buffer) = 0;
    virtual int submit(const uint32_t* commands, size_t count, uint32_t& outFence) = 0;
    virtual int waitFence(uint32_t fence, uint64_t timeoutNs) = 0;
};

// Fake GPU execution simulator for pre-flight testing and regression checks
class FakeGpuTransport : public Transport {
public:
    int allocate(size_t size, Buffer& outBuffer) override {
        outBuffer.handle = ++nextHandle_;
        outBuffer.size = size;
        outBuffer.hostPointer = ::operator new(size);
        outBuffer.gpuAddress = 0x50000000ULL + (outBuffer.handle * 0x100000ULL);
        return 0;
    }

    int free(Buffer& buffer) override {
        if (buffer.hostPointer) {
            ::operator delete(buffer.hostPointer);
            buffer.hostPointer = nullptr;
        }
        return 0;
    }

    int submit(const uint32_t* /*commands*/, size_t /*count*/, uint32_t& outFence) override {
        outFence = ++nextFence_;
        return 0;
    }

    int waitFence(uint32_t /*fence*/, uint64_t /*timeoutNs*/) override {
        return 0;
    }

private:
    uint32_t nextHandle_ = 0;
    uint32_t nextFence_ = 0;
};

} // namespace a05s::metal
