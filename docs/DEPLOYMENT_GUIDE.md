# Samsung Galaxy A05s (SM-A057F) - iOS 16 Port Deployment Guide

This guide describes how to replicate and deploy genuine Apple iOS 16 (Darwin XNU Kernel 22.6.0 / iOS 16.7.16 20H392) userspace on the **Samsung Galaxy A05s** (`SM-A057F`, Qualcomm Snapdragon 680 4G / `SM6225`, Longcheer `m269` motherboard).

---

## Architecture Overview

```
                      +---------------------------------------+
                      | Stock Samsung ABL (Unlocked BL)       |
                      +---------------------------------------+
                                          |
                                          v
                      +---------------------------------------+
                      | a05s-stage3-boot.img (Header v2 / v4) |
                      | - Shim ELF Loader (Silver CPU0 Entry) |
                      | - PSCI CPU_ON -> Kryo Gold Core (A73) |
                      | - Mach-O Kernel Payload + A05s ADT    |
                      +---------------------------------------+
                                          |
                                          v
                      +---------------------------------------+
                      | Darwin XNU 22.6.0 (ARM64_SWEET)       |
                      | - AppleCLCD Framebuffer (0x5C000000)  |
                      | - UFS 2.2 Controller (LUN 0 userdata) |
                      | - Case-Sensitive Apple HFS+ Mount     |
                      +---------------------------------------+
                                          |
                                          v
                      +---------------------------------------+
                      | iOS 16.7.16 Userspace (D22AP iPhone X)|
                      | - /sbin/launchd (PID 1)               |
                      | - containermanagerd, logd, launchd    |
                      | - com.apple.backboardd                |
                      | - SpringBoard.app (Lock Screen)       |
                      +---------------------------------------+
```

---

## Hardware & Environment Prerequisites

1. **Target Device:** Samsung Galaxy A05s (`SM-A057F`, `SM-A057F/DS`), unlocked bootloader.
2. **Recovery Environment:** OrangeFox Recovery (or TWRP) installed on the recovery partition.
3. **Host Computer:** Linux (Ubuntu 22.04+) or Windows 10/11 with Python 3.10+ and Android Platform Tools (`adb`, `fastboot`).
4. **USB Cable:** Quality USB Type-C data cable.
5. **Storage Requirement:** Minimum 32 GB free space on internal UFS (the `userdata` partition `/dev/block/sda36` is 111 GB).

---

## Step 1: Unlocking Bootloader & Disabling Samsung AVB

1. Enable **Developer Options** on your stock device and toggle **OEM Unlocking**.
2. Power off the phone, hold `Volume Up` + `Volume Down`, and connect the USB cable to enter Download Mode.
3. Long-press `Volume Up` to unlock the bootloader (this wipes all device data).
4. Flash an AVB-disabled `vbmeta.img` (`flags 0x3`):
   ```sh
   adb reboot recovery
   adb push out/vbmeta.img /tmp/vbmeta.img
   adb shell dd if=/tmp/vbmeta.img of=/dev/block/by-name/vbmeta
   ```

---

## Step 2: Building the Darwin XNU Kernel

### Option A: Automated GitHub Actions CI (Recommended)
This repository includes a fully automated macOS build harness (`.github/workflows/xnu.yml`):
```sh
gh workflow run xnu.yml -R seif-zone/ios-samsung-a05s --ref main
gh run download -R seif-zone/ios-samsung-a05s -n xnu-kernel -D out/artifacts/xnu-kernel
```

### Option B: Local Compilation
Using Apple's open-source XNU tree with the Sweet/A05s patch series:
```sh
cd xnu
# Apply patch series 0001 through 0952
git am patches/*.patch
./tools/build-local.sh
```

---

## Step 3: Preparing the iOS 16.7.16 RootFS

1. Download the official Apple IPSW for **iPhone X (iPhone10,3 / D22AP)**, build `16.7.16` (`20H392`):
   ```sh
   # IPSW: iPhone10,3_16.7.16_20H392_Restore.ipsw
   unzip -j iPhone10,3_16.7.16_20H392_Restore.ipsw "087-86698-044.dmg" "087-86593-047.dmg" "087-86715-047.dmg"
   ```
2. Unpack the OS RootFS DMG (`087-86698-044.dmg`) into `rootfs_build/os_root`.
3. Extract SystemOS and AppOS cryptex libraries and trampolines:
   ```sh
   python3 tools/extract_cryptex_files.py --root rootfs_build/os_root --sysos 087-86593-047.dmg --appos 087-86715-047.dmg
   ```
4. Apply launchd tweaks, permission fixes, and setup bypass plists:
   ```sh
   python3 tools/prepare_rootfs.py rootfs_build/os_root
   ```
5. Package the rootfs into a clean POSIX tarball preserving Unix symlinks:
   ```sh
   python3 tools/pack_rootfs_tar.py rootfs_build/os_root out/ios16-root.tar
   ```

---

## Step 4: Formatting the UFS Data Partition (HFS+)

Boot the Galaxy A05s into OrangeFox Recovery, connect via ADB, and format `/dev/block/sda36` as Case-Sensitive Apple HFS+:

```bat
:: Windows
tools\deploy\format_hfs_via_adb.bat
```

Or manually via bash:
```sh
adb push tools/bin/newfs_hfs_static /tmp/newfs_hfs_static
adb push tools/bin/hfs_static /tmp/hfs_static
adb shell "chmod +x /tmp/newfs_hfs_static /tmp/hfs_static"
adb shell "umount /data 2>/dev/null; umount /dev/block/sda36 2>/dev/null"
adb shell "/tmp/newfs_hfs_static -s -v iOSRoot -b 4096 /dev/block/sda36"
```

---

## Step 5: Deploying the iOS RootFS & Setting Permissions

Deploy the rootfs tarball directly into the freshly formatted HFS+ volume:
```sh
adb push out/ios16-root.tar /tmp/ios16-root.tar
adb push tools/deploy/deploy_ios_hfs.sh /tmp/deploy_ios_hfs.sh
adb shell "chmod +x /tmp/deploy_ios_hfs.sh && /tmp/deploy_ios_hfs.sh"
```

Or run the Stage 3 finalizer to ensure SpringBoard permissions (`chmod 755`), `/private/var/mobile` ownership, and container directories:
```sh
adb push tools/deploy/finalize_stage3.sh /tmp/finalize_stage3.sh
adb shell "chmod +x /tmp/finalize_stage3.sh && /tmp/finalize_stage3.sh"
```

---

## Step 6: Building the Boot Image & Flashing

Generate the Apple Device Tree (ADT) and package the bootable image:

```sh
# 1. Compile Apple Device Tree for A05s
python3 tools/mkadt.py out/a05s.adt

# 2. Package Stage 3 Boot Image & Odin TAR
python3 tools/deploy/build_stage3_kernel.py
```

### Flashing via Recovery (Fastest):
```sh
adb push out/a05s-stage3-boot.img /tmp/boot.img
adb shell "dd if=/tmp/boot.img of=/dev/block/by-name/boot"
adb reboot
```

### Flashing via Samsung Odin:
1. Boot phone into Download Mode (Power + Vol Up + Vol Down with USB plugged in).
2. Load `out/AP_A05s_iOS16_Stage3_GUI.tar.md5` into Odin's **AP** slot.
3. Click **Start** to flash the NAND partition.

---

## Step 7: Reading Persistent Boot Logs

Darwin XNU logs all serial console output directly to a persistent 4 MiB ring buffer at the tail end of the UFS partition. To inspect logs after any boot or crash:

1. Reboot the device into Recovery (`Power` + `Volume Up`).
2. Run the extraction utility:
   ```sh
   python3 tools/deploy/pull_boot_log.py boot_panic_log.txt
   ```
3. The complete console log (including `launchd`, `backboardd`, and `SpringBoard` events) will be saved in `boot_panic_log.txt`.

---

## License & Credits

- Darwin XNU is licensed under Apple Public Source License (APSL 2.0).
- Bring-up research and Qualcomm SM6225 porting by **Seif** ([@seif-zone](https://github.com/seif-zone)).
- Upstream Qualcomm bootloader shim research by dipa-studio and HakiOS team.
