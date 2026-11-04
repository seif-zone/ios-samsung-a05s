# ios-samsung-a05s

**Apple's iOS 16 (Darwin XNU) running on Samsung Galaxy A05s (SM-A057F / m269).**

This is a port of Apple's open-source XNU kernel (`xnu-8796`, iOS 16 era) and userland to the **Samsung Galaxy A05s** (`SM-A057F`, Qualcomm **SM6225 / Snapdragon 680 4G**, Longcheer motherboard codename `m269`). On top of it runs the **unmodified iOS 16.7.16 (20H392) userland of the iPhone X**: `launchd`, system daemons, `backboardd`, and `SpringBoard`.

Ported and maintained by **Seif** ([@seif-zone](https://github.com/seif-zone)).

Built upon the pioneering Qualcomm bring-up work of [ios-topaz](https://github.com/dipa-studio) and [dipa-studio/ios-sweet](https://github.com/dipa-studio/ios-sweet) (Redmi Note 10 Pro / Redmi Note 12 4G), and aligned with the [HakiOS project](https://hackios-web.vercel.app/en) by [OOSEX GANG](https://github.com/oosexgang/hakios-xnu-kernel).

> **Notice:** Experimental low-level bring-up. Many peripheral drivers are stubbed or in progress. This project runs entirely out of RAM or dedicated partitions; the kernel is loaded over USB via `fastboot boot` without writing or bricking stock boot partitions.

---

## Current Status

| Subsystem | Status | Implementation Details |
| :--- | :--- | :--- |
| **Bootloader** | Working | Stock Samsung ABL (unlocked) &rarr; `fastboot boot` of `a05s-boot.img` (Header Version 2) &rarr; `shim` &rarr; XNU. |
| **CPU (SMP)** | Working | 4&times; Kryo 260 Gold (Cortex-A73, MPIDR `0x100`..`0x103`), 16K pages, GICv3, ARM generic timers. Silver cores parked (see below). |
| **Memory** | Working | RAM base `0xb0000000`, 4 GiB / 6 GiB LPDDR4X support. All reserved carve-outs (Modem, ADSP, CDSP, Splash) protected below `0x63900000`. |
| **Display** | Working | PLS LCD (1080&times;2400). Scans out from the continuous splash buffer at `0x5C000000` (15 MB carveout, stride 4320). Handed to iOS as iPhone X canvas (`1125x2436`). |
| **GPU / Metal** | Partial | Adreno 610 (a6xx). PM4 packet generator and `hakios-metal` blit encoder pipeline integrated under `userland/metal/`. |
| **Battery / Gauge** | Working | Silicon Mitus SM5602 fuel gauge (`0x71`) routed through Qualcomm QUP0 SE2 (`0x04a88000`) on GPIO 6/7 (patch `0951`). |
| **Storage / RootFS** | Working | Native UFS 2.2 storage (`/dev/block/sda36`, 111 GB userdata). Mounted read-write as Case-Sensitive Apple HFS+ (`ufsroot0`), containing complete genuine iOS 16.7.16 userspace and Dyld shared cache. |
| **Touchscreen** | In progress | Chipone TDDI / Ilitek on `qupv3_se0_spi` (`0x04a80000`), Reset = GPIO 86, IRQ = GPIO 80 on TLMM WEST tile. |
| **Keys** | In progress | PMIC PM6125 power key and volume keys via TLMM GPIOs. |
| **Identity** | Working | Reported as iPhone X (`iPhone10,3` / `D22AP`) with gesture UI and modern SpringBoard layout. |

> 📘 **Step-by-Step Guide:** Looking to replicate this port on your device? Check out the comprehensive [Deployment Guide](docs/DEPLOYMENT_GUIDE.md).

---

## HakiOS Ecosystem Alignment

This project is structured in full alignment with the [HakiOS project](https://hackios-web.vercel.app/en):
- **Upstream Kernel:** [`oosexgang/hakios-xnu-kernel`](https://github.com/oosexgang/hakios-xnu-kernel)
- **Reference Device:** [`oosexgang/hakios-sm7325`](https://github.com/oosexgang/hakios-sm7325) (POCO X5 Pro 5G)
- **UEFI Bootloader:** [`oosexgang/hakios-uefi`](https://github.com/oosexgang/hakios-uefi)
- **Metal Driver:** [`oosexgang/hakios-metal`](https://github.com/oosexgang/hakios-metal)
- **Full Compatibility Guide:** See [HAKIOS.md](HAKIOS.md) for deep architectural comparisons.

### Standard Device Files
- [`device.conf`](device.conf): Formal device definition and component status table following HakiOS standards.
- [`soc.args`](soc.args): Hardware register coordinates for Qualcomm Snapdragon 680 (SM6225).
- [`configs/a057f.config`](configs/a057f.config): Driver switches and boot arguments.
- [`pull-firmware.sh`](pull-firmware.sh): Isolated ADB extraction of Adreno 610 zap shader and firmware into gitignored `fw-*/`.
- [`userland/metal/`](userland/metal/): Adreno 610 Metal PM4 command buffer builder and verification probe (`a05s_metal_probe.cpp`).

---

## How Samsung Galaxy A05s (`m269`) differs from Topaz & Sweet

Longcheer's Samsung A05s platform shares the Qualcomm SM6225 SoC with Xiaomi's topaz, but introduces critical platform and board-level divergences that silently break generic boot images:

| Hardware / Subsystem | Xiaomi Topaz / Sweet | Samsung Galaxy A05s (`m269`) | Fix / Adaptation in this Port |
| :--- | :--- | :--- | :--- |
| **Boot Image Header** | Header Version 4 | **Header Version 2** (`BOARD_BOOTIMG_HEADER_VERSION := 2`) | `shim/build-a05s.sh` enforces `--header_version 2`, `--base 0x00000000`, `--pagesize 4096`. Samsung ABL rejects v4 images. |
| **Internal Storage** | UFS 2.2 / 3.0 (`0x04804000`) | **eMMC 5.1** (`sdhci@7804000`) | XNU UFS driver panics when probing missing hardware. Booted via **MockFS / Ramdisk (`rd=md0`)** embedded directly into the payload. |
| **Fuel Gauge I2C Bus** | QUP0 SE1 (`0x04a84000`), GPIO 4/5 | **QUP0 SE2 (`0x04a88000`)**, GPIO 6/7 | Patch `0951-a05s-hardware-adaptations.patch`: reconfigures GCC clock branch `qupv3_wrap0_s2` and routes to TLMM WEST tile pins 6 & 7. |
| **Touchscreen Bus** | I2C (FocalTech FT5452 at `0x38`) | **SPI (`qupv3_se0_spi` at `0x04a80000`)** | Hardware mapping updated for SPI TDDI controller (Chipone / Ilitek) with GPIO 86 Reset and GPIO 80 IRQ. |
| **Display Panel** | AMOLED (1080&times;2400) | **PLS LCD (1080&times;2400)** | Native 1080&times;2400 framebuffer at `0x5C000000` preserved across boot; LCD bias powered by `pm6125_gpios 6`. |

---

## CPU Architecture: Why only the Gold cores?

The Snapdragon 680 (SM6225) combines two core types:
- **4&times; Kryo 260 Silver:** Cortex-A53 class, MPIDR `0x0`..`0x3`. **Lacks 16K translation granule** (`ID_AA64MMFR0_EL1.TGran16 = 0`).
- **4&times; Kryo 260 Gold:** Cortex-A73 class, MPIDR `0x100`..`0x103`. Supports 16K granule (`TGran16 != 0`).

XNU requires 16K translation granule for both kernel and iOS 16 userland (hardcoded into `mach_vm`, `malloc`, and dyld shared cache). The `shim` starts execution on Silver CPU 0, detects `TGran16 = 0`, calls PSCI `CPU_ON(0x100, secondary_entry, 4)` to wake Gold CPU 0, and parks Silver in a low-power `wfi` loop. XNU boots exclusively on the Gold cores.

```
Samsung ABL (unlocked)
  -> fastboot boot a05s-boot.img                  (Boot v2, RAM only)
     -> shim on Silver CPU0: reads MMFR0, wakes Gold CPU 0x100 via PSCI, parks in WFI
        -> shim on Gold CPU 0: sets up GICv3, locates XNU payload behind _end
           -> XNU Mach-O + Apple Device Tree (ADT) + boot-args
              -> Mounts MockFS / Ramdisk (/dev/md0)
                 -> dyld + shared cache -> launchd (PID 1) -> SpringBoard
```

---

## Building and Packaging

### 1. Build the Darwin XNU Kernel
The kernel compiles via GitHub Actions (`.github/workflows/xnu.yml`) on macOS-14 runners with Xcode 15 and Blacktop's XNU build harness:

```sh
gh workflow run xnu.yml -R seif-zone/ios-samsung-a05s --ref main
gh run download -R seif-zone/ios-samsung-a05s -n xnu-kernel -D out/artifacts/xnu-kernel
```

### 2. Generate Apple Device Tree (ADT) and Payload
Generate the Samsung A05s device tree and resolve unslid chained fixups into the bootable XNU payload:

```sh
# Generate A05s Apple Device Tree
python3 tools/mkadt.py out/a05s.adt

# Pack Mach-O kernel + ADT into payload
python3 tools/mkpayload.py out/artifacts/xnu-kernel/kernel.development.sweet out/a05s.adt out/a05s.payload \
    --cmdline "console=null earlycon=msm_geni_serial,0x4a90000 sweetfb_console=1 cpus=4 debug=0x14e rd=md0 -v"
```

### 3. Pack Samsung Boot Image (Header Version 2)
Cross-compile the A05s `shim` with aarch64 toolchain, append payload, and pack with Samsung header v2:

```sh
bash shim/build-a05s.sh out/a05s.payload
# Outputs: shim/out/a05s-boot.img
```

---

## Boot Simulation & Pre-Flight Verifier

### 1. Offline Pre-Flight Verifier
Run the standalone pre-flight script to parse the payload and ADT, verifying entry points, memory carveouts, and PSCI handoffs:
```sh
python3 tools/sim-preflight.py out/a05s.payload out/a05s.adt
```

### 2. Interactive Boot Simulator (Web UI)
An interactive simulation engine is available in `docs/index.html` (viewable directly in your browser or deployed via GitHub Pages), simulating the transition from Samsung ABL to shim on Silver core, PSCI wake-up of Gold CPU 0, Darwin XNU kernel initialization, MockFS Ramdisk mount, and SpringBoard handoff on an accurate model of the Samsung Galaxy A05s.

---

## Booting on Device (Fastboot Tethered Boot)

> **Safe Testing:** Always use `fastboot boot` to run from RAM without flashing or modifying physical partitions.

1. Unlock the bootloader via Samsung Developer Settings (`OEM unlocking`) and Odin Device Unlock Mode.
2. Put the device into Fastboot mode:
   ```sh
   adb reboot bootloader
   ```
3. Boot the image directly in RAM:
   ```sh
   fastboot boot shim/out/a05s-boot.img
   ```
4. To return to stock Samsung One UI Android, simply hold **Power + Volume Down** to reboot normally.

---

## Repository Structure

```
├── .github/workflows/    # Automated CI/CD kernel compilation pipelines
├── configs/              # HakiOS driver configurations (a057f.config)
├── device.conf           # HakiOS device metadata & component status
├── soc.args              # Snapdragon 680 (SM6225) register coordinates
├── pull-firmware.sh      # Isolated ADB firmware extractor
├── HAKIOS.md             # In-depth HakiOS integration & compatibility guide
├── shim/                 # Bare-metal A05s boot shim, Gold CPU PSCI handoff, GICv3 setup
│   ├── build-a05s.sh     # Samsung Boot Header v2 packaging pipeline
│   ├── shim.c            # Core CPU & MMU initialization
│   └── loader.c          # Embedded XNU payload unpacker
├── tools/
│   ├── bin/                  # Precompiled ARM64 static binaries (hfs_static, newfs_hfs_static)
│   ├── deploy/               # Stage 3 automated deployment and log extraction suite
│   │   ├── build_stage3_kernel.py  # Stage 3 Kernel, boot.img & Odin TAR packager
│   │   ├── pull_boot_log.py        # Persistent UFS console log reader
│   │   ├── deploy_ios_hfs.sh       # In-recovery HFS+ automated unpacker
│   │   ├── finalize_stage3.sh      # Permissions, SpringBoard chmod & setup bypass
│   │   └── format_hfs_via_adb.bat  # 1-click ADB HFS+ formatting script
│   ├── mkadt.py              # Apple Device Tree generator (samsung,a05s & m269 node)
│   ├── mkpayload.py          # Mach-O chained fixup resolver and payload builder
│   ├── pack_a05s_all.py      # Complete Boot Header v4 & OrangeFox flashable bundle generator
│   ├── prepare_rootfs.py     # Stage 2 RootFS builder & sweet tweaks applicator
│   ├── extract_cryptex_files.py # APFS Cryptex decompressor via dissect.apfs
│   ├── pack_rootfs_tar.py    # POSIX tar packager preserving UIDs, GIDs, modes, and symlinks
│   ├── install_ios_root.sh   # Automated deployment script for OrangeFox Recovery
│   └── restore_android.sh    # Instant Android Custom ROM (One UI 6 / S901E) restoration script
├── userland/                 # GPU injection, EAGL shim, and audio HAL plugins
│   └── metal/                # Adreno 610 Metal PM4 command buffer builder & probe
└── xnu/patches/              # Patch series applied cleanly to Apple XNU 8796 tree
    ├── 0080-0082             # SM6225 architecture and Gold CPU topology
    └── 0951                  # Samsung A05s SM5602 gauge on SE2 (GPIO 6/7)
```

---

## Stage 2: iOS 16 RootFS & MicroSD Deployment

The Stage 2 pipeline constructs the full official **iOS 16.7.16 (`20H392`)** root filesystem from Apple IPSW (`iPhone10,3,iPhone10,6_16.7.16_20H392_Restore.ipsw`) and prepares it for safe MicroSD deployment:

1. **RootFS Assembly:**
   - Unpacks OS Root DMG (`087-86698-044.dmg`) containing `/sbin/launchd`, `/usr/libexec/backboardd`, and `/System/Library/CoreServices/SpringBoard.app`.
   - Integrates SystemOS Cryptex (`087-86593-047.dmg`) and AppOS Cryptex (`087-86715-047.dmg`) under `/private/preboot/Cryptexes/`.
   - Extracted and linked the unified `dyld_shared_cache_arm64` into `/System/Library/Caches/com.apple.dyld/` (where `ignition_level=1` reads it).
   - Decompressed all LZBITMAP trampolines (`libobjc-trampolines.dylib`, `libffi-trampolines.dylib`, `libstdc++.6.0.9.dylib`) into `/usr/lib/`.

2. **HakiOS & SWEET Bring-Up Tweaks:**
   - `System/Library/xpc/launchd.plist`: Renamed `_PanicOnCrash` &rarr; `_PanicOnCrasX` (preventing panics on daemon faults) and stripped `com.apple.CommCenter`.
   - `/private/var/containers/`: Generated `Bundle`, `Data/System`, `Shared/SystemGroup`, and `Temp`.
   - `mobileactivationd`: Seeded `data_ark.plist` with `-ActivationState: Activated`.
   - Preferences: Set `LastSystemVersion = 20H392` (skipping the 1-hour data migration) and `BKNoWatchdogs = true` in SpringBoard.
   - Keybags: Created `/private/var/keybags/systembag.kb` for AppleKeyStore.
   - Log stores: Created `/private/var/db/diagnostics/.migrated` and `uuidtext/.migrated`.

3. **Safe Dual-Boot via MicroSD:**
   - Use OrangeFox Recovery to create a 1-click backup of `Data` (`userdata`) directly to MicroSD.
   - Run `sh /external_sd/install_ios_root.sh` in OrangeFox to unpack `ios16-root.tar`.
   - Flash `a05s-ios-orangefox.zip` containing `a05s-boot-v4.img` and patched `vbmeta.img`.
   - When returning to Android: Run `sh /external_sd/restore_android.sh` or tap `Restore` in OrangeFox. Zero risk of data loss.

---

## Credits and Acknowledgments

- **Lead Developer & Maintainer:** **Seif** ([@seif-zone](https://github.com/seif-zone)) &ndash; Samsung Galaxy A05s port, Samsung ABL Header v2 packaging, Longcheer `m269` devicetree & register mapping, SM5602 SE2 adaptations, eMMC MockFS integration, HakiOS alignment.
- **HakiOS Team:** [OOSEX GANG](https://github.com/oosexgang/hakios-xnu-kernel) &ndash; HakiOS architecture, drivers configuration standard, `hakios-metal` Adreno Metal command pipeline, and `hakios-sm7325` reference bring-up.
- **ios-topaz & ios-sweet teams:** [dipa-studio](https://github.com/dipa-studio/ios-sweet) &ndash; Qualcomm SM6225 architecture foundation, Cortex-A53 PFZ atomics emulation, PSCI Gold CPU wake-up handoff.
- **blacktop:** [darwin-xnu-build](https://github.com/blacktop/darwin-xnu-build) &ndash; Automated XNU compilation harness.
- **Apple Inc.:** Darwin XNU Kernel releases (APSL 2.0).

See [CREDITS.md](CREDITS.md) for full licensing details.
