# ios-samsung-a05s

**Apple's iOS 16 (Darwin XNU) running on Samsung Galaxy A05s (SM-A057F / m269).**

This is a port of Apple's open-source XNU kernel (`xnu-8796`, iOS 16 era) and userland to the **Samsung Galaxy A05s** (`SM-A057F`, Qualcomm **SM6225 / Snapdragon 680 4G**, Longcheer motherboard codename `m269`). On top of it runs the **unmodified iOS 16.7.16 (20H392) userland of the iPhone X**: `launchd`, system daemons, `backboardd`, and `SpringBoard`.

Ported and maintained by **Seif** ([@seif-zone](https://github.com/seif-zone)).

Built upon the pioneering Qualcomm bring-up work of [ios-topaz](https://github.com/dipa-studio) and [dipa-studio/ios-sweet](https://github.com/dipa-studio/ios-sweet) (Redmi Note 10 Pro / Redmi Note 12 4G), with GPU & audio infrastructure derived from [HackiOS](https://github.com/oosexgang/hackios-xnu-kernel) by OOSEX GANG.

> **Notice:** Experimental low-level bring-up. Many peripheral drivers are stubbed or in progress. This project runs entirely out of RAM or dedicated partitions; the kernel is loaded over USB via `fastboot boot` without writing or bricking stock boot partitions.

---

## Current Status

| Subsystem | Status | Implementation Details |
| :--- | :--- | :--- |
| **Bootloader** | Working | Stock Samsung ABL (unlocked) &rarr; `fastboot boot` of `a05s-boot.img` (Header Version 2) &rarr; `shim` &rarr; XNU. |
| **CPU (SMP)** | Working | 4&times; Kryo 260 Gold (Cortex-A73, MPIDR `0x100`..`0x103`), 16K pages, GICv3, ARM generic timers. Silver cores parked (see below). |
| **Memory** | Working | RAM base `0x40000000`, 4 GiB / 6 GiB LPDDR4X support. All reserved carve-outs (Modem, ADSP, CDSP, Splash) protected below `0x63900000`. |
| **Display** | Working | PLS LCD (1080&times;2400). Scans out from the continuous splash buffer at `0x5C000000` (15 MB carveout, stride 4320). Handed to iOS as iPhone X canvas (`1125x2436`). |
| **Battery / Gauge** | Working | Silicon Mitus SM5602 fuel gauge (`0x71`) routed through Qualcomm QUP0 SE2 (`0x04a88000`) on GPIO 6/7 (patch `0951`). |
| **Storage / RootFS** | Working | eMMC 5.1 (`sdhci@7804000`). Boots cleanly via embedded **MockFS / Ramdisk (`rd=md0`)** inside payload, bypassing missing UFS controllers. |
| **Touchscreen** | In progress | Chipone TDDI / Ilitek on `qupv3_se0_spi` (`0x04a80000`), Reset = GPIO 86, IRQ = GPIO 80 on TLMM WEST tile. |
| **Keys** | In progress | PMIC PM6125 power key and volume keys via TLMM GPIOs. |
| **Identity** | Working | Reported as iPhone X (`iPhone10,3` / `D22AP`) with gesture UI and modern SpringBoard layout. |

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
├── shim/                 # Bare-metal A05s boot shim, Gold CPU PSCI handoff, GICv3 setup
│   ├── build-a05s.sh     # Samsung Boot Header v2 packaging pipeline
│   ├── shim.c            # Core CPU & MMU initialization
│   └── loader.c          # Embedded XNU payload unpacker
├── tools/
│   ├── mkadt.py          # Apple Device Tree generator (samsung,a05s & m269 node)
│   ├── mkpayload.py      # Mach-O chained fixup resolver and payload builder
│   ├── mkinit.py         # Static ad-hoc signed Mach-O init wrapper
│   └── sweet-init.S      # Standalone PID 1 early userspace verification
├── userland/             # GPU injection, EAGL shim, and audio HAL plugins
└── xnu/patches/          # Patch series applied cleanly to Apple XNU 8796 tree
    ├── 0080-0082         # SM6225 architecture and Gold CPU topology
    └── 0951              # Samsung A05s SM5602 gauge on SE2 (GPIO 6/7)
```

---

## Credits and Acknowledgments

- **Lead Developer & Maintainer:** **Seif** ([@seif-zone](https://github.com/seif-zone)) &ndash; Samsung Galaxy A05s port, Samsung ABL Header v2 packaging, Longcheer `m269` devicetree & register mapping, SM5602 SE2 adaptations, eMMC MockFS integration.
- **ios-topaz & ios-sweet teams:** [dipa-studio](https://github.com/dipa-studio/ios-sweet) &ndash; Qualcomm SM6225 architecture foundation, Cortex-A53 PFZ atomics emulation, PSCI Gold CPU wake-up handoff.
- **HackiOS:** [OOSEX GANG](https://github.com/oosexgang/hackios-xnu-kernel) &ndash; GPU (Adreno / Mesa freedreno), display presentation, RedwoodAudio HAL.
- **blacktop:** [darwin-xnu-build](https://github.com/blacktop/darwin-xnu-build) &ndash; Automated XNU compilation harness.
- **Apple Inc.:** Darwin XNU Kernel releases (APSL 2.0).

See [CREDITS.md](CREDITS.md) for full licensing details.
