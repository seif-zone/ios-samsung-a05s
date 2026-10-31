# HakiOS Integration & Compatibility Architecture
### Samsung Galaxy A05s (`SM-A057F` / `m269` / Qualcomm Snapdragon 680 `SM6225`)

This document details how this repository aligns with the upstream [HakiOS project](https://hackios-web.vercel.app/en) and its ecosystem repositories:
- **Upstream Kernel:** [`oosexgang/hakios-xnu-kernel`](https://github.com/oosexgang/hakios-xnu-kernel)
- **Reference Device (POCO X5 Pro):** [`oosexgang/hakios-sm7325`](https://github.com/oosexgang/hakios-sm7325)
- **UEFI Bootloader:** [`oosexgang/hakios-uefi`](https://github.com/oosexgang/hakios-uefi)
- **Metal Acceleration Driver:** [`oosexgang/hakios-metal`](https://github.com/oosexgang/hakios-metal)
- **Official Documentation:** [`hackios-web.vercel.app`](https://hackios-web.vercel.app/en)

---

## 1. Architectural Comparison: POCO X5 Pro (`redwood`) vs. Samsung Galaxy A05s (`m269`)

| Component | POCO X5 Pro 5G (`redwood`) | Samsung Galaxy A05s (`SM-A057F` / `m269`) | Architectural Impact on Port |
|---|---|---|---|
| **SoC** | Qualcomm Snapdragon 778G (`SM7325` / `sc7280`) | Qualcomm Snapdragon 680 (`SM6225` / `bengal`) | Different register base addresses (`soc.args`), GICv3 offsets, and OPP clock steps. |
| **CPU Cluster** | 4x Cortex-A78 + 4x Cortex-A55 | 4x Kryo 260 Gold (A73) + 4x Kryo 260 Silver (A53) | **CRITICAL:** Cortex-A53 lacks 16KB translation granule (`TGran16 = 0`). Boot requires PSCI handoff to Kryo Gold! |
| **Bootloader** | Little Kernel (ABL) with Mu-Silicium UEFI port | Samsung Knox ABL (Little Kernel) | Samsung ABL strictly enforces **Android Boot Image Header Version 2** (4096-byte pages). Header v3/v4 is rejected. |
| **GPU** | Adreno 642L | Adreno 610 | Both are Qualcomm A6xx architecture; both use the exact same PM4 packet format and command processor. |
| **Storage** | UFS 2.2 (`ufs@1d84000`) | eMMC 5.1 (`sdhci@7804000`) | RAM-only MockFS rootfs (`rd=md0`) provides identical safe execution across both without storage writes. |
| **Battery Gauge**| Audio DSP proxy | SM5602 I2C Fuel Gauge | Routed via QUP0 SE2 (`0x04a88000`) on TLMM West GPIO 6/7. |

---

## 2. Boot Protocol & Zero-Flashing Policy

Following the HakiOS core philosophy:
> *"By default the loader goes into RAM through `fastboot boot`, the system lives in RAM for a session, and a reboot brings the phone back to its own Android."*

Our port adheres strictly to this zero-risk execution method:
1. **Host PC:** Prepares the self-contained boot package:
   ```bash
   tools/mkbootimg.py \
     --kernel shim/shim.bin \
     --ramdisk out/a05s.payload \
     --base 0x00000000 \
     --pagesize 4096 \
     --header_version 2 \
     --cmdline "earlycon=msm_geni_serial,0x04a90000 serial=3 debug=0x14e rd=md0 phys_base=0xb0000000" \
     -o out/a05s-boot.img
   ```
2. **Device Deployment (No Flashing!):**
   ```bash
   fastboot boot out/a05s-boot.img
   ```
3. **Execution:** The entire Darwin kernel, MockFS ramdisk, and userland run solely within DDR RAM (`0xb0000000` carve-out). A simple power off or reboot immediately returns the phone to stock One UI Android.

---

## 3. The 16KB Page Granule Challenge (`TGran16`)

Darwin XNU is strictly compiled for 16KB memory pages (`PAGE_SIZE = 16384`).
- On ARMv8-A, hardware support for 16KB pages is indicated by `ID_AA64MMFR0_EL1[23:20]` (`TGran16` field):
  - Value `1` or `2`: 16KB translation granule supported.
  - Value `0`: 16KB translation granule unsupported (4KB and 64KB only).
- In the Qualcomm Snapdragon 680 (`SM6225`), the LITTLE cluster (Kryo 260 Silver / Cortex-A53) has `TGran16 = 0`.
- The Samsung ABL bootloader always branches to the kernel entry point on CPU 0 (Silver Core 0).
- **The Solution:** Our bare-metal `shim/shim.c` intercepts boot at EL2/EL1, verifies `TGran16`:
  ```c
  uint64_t mmfr0;
  asm volatile("mrs %0, id_aa64mmfr0_el1" : "=r"(mmfr0));
  if (((mmfr0 >> 20) & 0xf) == 0) {
      // Awaken Kryo Gold Core 0 (MPIDR 0x100) via PSCI
      smc(0xc4000003, 0x100, (uintptr_t)secondary_entry, 0);
      // Park Silver CPU in low-power WFI
      while (1) asm volatile("wfi");
  }
  ```
  Kryo Gold Core 0 awakens, inherits the environment with native 16KB support, and executes Darwin XNU safely.

---

## 4. Metal GPU Acceleration on Adreno 610

We adopt the architecture of [`oosexgang/hakios-metal`](https://github.com/oosexgang/hakios-metal) for the Adreno 610 GPU:
- **PM4 Command Processor:** Uses Type 4 (register writes) and Type 7 (engine commands like `CP_MEMCPY`, `CP_WAIT_FOR_IDLE`) packets with odd-parity validation bits.
- **Hardware Blit Pipeline:** Metal `MTLBlitCommandEncoder` translates buffer copies and fills directly into Adreno PM4 packets (`pm4.hpp`), bypassing Mesa CPU copy loops.
- **Userspace Driver:** `userland/metal/` provides the C++ abstraction layer connecting `libhakios-metal.a` to the kernel's DRM interface.

---

## 5. Standard HakiOS Device Files

This repository contains standard metadata files for direct inclusion in the HakiOS device tree:
- [`device.conf`](device.conf): Formal device definition and hardware component status table.
- [`soc.args`](soc.args): Hardware register coordinates for Qualcomm SM6225.
- [`configs/a057f.config`](configs/a057f.config): Kernel drivers and boot-args.
- [`pull-firmware.sh`](pull-firmware.sh): Isolated ADB extraction of Adreno 610 zap shader and firmware into gitignored `fw-*/`.
