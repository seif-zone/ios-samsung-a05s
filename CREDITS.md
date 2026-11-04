# Credits and Licences

## Samsung Galaxy A05s (SM-A057F / m269) Port

- **Port Lead & Maintainer:** **Seif** ([@seif-zone](https://github.com/seif-zone))
  - Samsung Galaxy A05s platform bring-up.
  - Samsung ABL Android Boot Header Version 4 implementation for GKI (`BOARD_BOOTIMG_HEADER_VERSION := 4`).
  - Qualcomm SM6225 / Khaje register mapping for Longcheer `m269` devicetree.
  - Silicon Mitus SM5602 battery fuel gauge adaptation on QUP0 SE2 (`0x04a88000`) on GPIO 6/7 (TLMM WEST tile).
  - eMMC 5.1 storage bypass via embedded MockFS / Ramdisk (`rd=md0`) payload bootstrap.
  - Apple Device Tree (ADT) hardware definition for `samsung,a05s` and `samsung,m269`.
  - HakiOS ecosystem integration, `device.conf`, `soc.args`, and Adreno 610 Metal PM4 command driver integration.

---

## Upstream Projects and Core Contributors

### HakiOS (OOSEX GANG)

Much of the core XNU driver architecture, display presentation, audio, Wi-Fi glue, sandbox infrastructure, and Metal GPU acceleration originates from **HakiOS**, which boots XNU and iOS 16 user space on Qualcomm Android phones:

- **Documentation:** <https://hackios-web.vercel.app/en>
- **Kernel & Drivers:** <https://github.com/oosexgang/hakios-xnu-kernel> &ndash; Apple Public Source License 2.0
- **POCO X5 Pro (redwood):** <https://github.com/oosexgang/hakios-sm7325>
- **UEFI Firmware:** <https://github.com/oosexgang/hakios-uefi> &ndash; Mu-Silicium (BSD-2-Clause-Patent)
- **Metal Acceleration Driver:** <https://github.com/oosexgang/hakios-metal> &ndash; MIT License, Copyright (c) 2026 OOSEX GANG

#### Kernel patches derived from HakiOS (APSL 2.0)
`xnu/patches/0900-*` and `0901-*` through `0947-*` contain, adapted and modified: `RedwoodGPU.cpp` (msm-style GPU client), `MiniIOMobileFramebuffer` presentation pipeline (SwapEnd handed to presenter thread, vsync notification layout), `redwood_apple80211` / `redwood_sta` / `redwood_net` (Apple80211 for `wifid`), `/dev/redwood-audio` interface, minisandbox container path, and `kern.exec_inject`. Like XNU itself, these files are under APSL 2.0.

#### User space & Metal derived from HakiOS (MIT)
`userland/gpu/eagl.c`, `userland/gpu/gl_osmesa.c`, `userland/gpu/inject.c`, `userland/metal/*` (PM4 packet processor, Adreno GEM transport, command buffer encoder), and `userland/audio/*` are licensed under MIT:

```
MIT License

Copyright (c) 2026 OOSEX GANG

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

### ios-topaz & ios-sweet

- **ios-topaz:** Architecture foundation for Qualcomm Snapdragon 680/685 (SM6225 / Khaje), Cortex-A53 PFZ atomics emulation, and PSCI Gold CPU wake-up handoff.
- **ios-sweet (dipa-studio):** <https://github.com/dipa-studio/ios-sweet> &ndash; The original Darwin XNU port on Qualcomm hardware and iPhone X userland bring-up.

---

### Tools and Components

- **Apple Inc.:** Darwin XNU Kernel (APSL 2.0), IOHIDFamily, libpthread, and HFS filesystem.
- **blacktop:** [darwin-xnu-build](https://github.com/blacktop/darwin-xnu-build) &ndash; Automated XNU compilation harness.
- **Mesa / freedreno:** Open-source OpenGL ES driver for Adreno graphics.
- **BearSSL:** Embedded SSL/TLS implementation.
