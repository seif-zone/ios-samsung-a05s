# Samsung Galaxy A05s (SM-A057F) - Stock Recovery & Unbrick Runbook

This runbook describes how to safely restore the **Samsung Galaxy A05s** (`SM-A057F` / `m269`, Qualcomm Snapdragon 680 `SM6225`) back to factory stock Samsung One UI Android firmware, or recover from bootloops and experimental kernel states.

---

## Important Notice on Samsung Hardware

Unlike Xiaomi, Google Pixel, or OnePlus devices, retail **Samsung Galaxy devices do not have a native bootloader Fastboot mode**.
- Samsung Knox ABL uses **Samsung Download Mode (ODIN Mode)** implementing the proprietary LOKE / ODIN protocol.
- Standard fastboot commands (`fastboot boot`, `fastboot flash`) are **unsupported** on the Samsung retail bootloader.
- All complete restores and firmware unbricking are executed using **Samsung Odin v3.14.4+** on Windows, or `heimdall` on Linux.

---

## 1. Required Firmware Files

To restore stock Android One UI, use the official Samsung 4-piece / 5-piece firmware package:

| Slot | File Pattern | Contents |
| :--- | :--- | :--- |
| **BL** | `BL_A057FXXU...tar.md5` | Primary bootloader, Secondary bootloader (ABL), XBL, TrustZone, RPM |
| **AP** | `AP_A057FXXU...tar.md5` | Stock Android GKI Boot (`boot.img` Header v4), System, Vendor, Product, VBMeta |
| **CP** | `CP_A057FXXU...tar.md5` | Modem firmware and radio baseband |
| **CSC** | `CSC_...tar.md5` or `HOME_CSC_...` | Partition table (PIT) and regional carrier customization (`CSC` wipes userdata; `HOME_CSC` preserves user data) |

---

## 2. Entering Samsung Download Mode (ODIN Mode)

### Method A: From Running Android or Custom Recovery (ADB)
```sh
adb reboot download
```

### Method B: Hardware Key Combination (Power Off / Bootloop)
1. Turn off the device completely (or hold **Power + Volume Down** until the screen turns black).
2. Connect a USB Type-C data cable to your PC (do **not** connect it to the phone yet).
3. Press and hold both **Volume Up** and **Volume Down** buttons simultaneously.
4. While holding both buttons, insert the USB Type-C cable into the phone.
5. Release both buttons when the cyan/teal **Warning / Download Mode** screen appears.
6. Press **Volume Up** once to confirm and enter **ODIN Mode (Downloading)**.

---

## 3. Flashing Stock Firmware via Samsung Odin

1. Launch **Odin3 v3.14.4** on Windows.
2. Verify that Odin detects the device (the top-left box **ID:COM** will turn light blue and show `[Added!!]`).
3. Load the firmware files into their corresponding slots:
   - Click **BL** and select `BL_A057FXXU...tar.md5`.
   - Click **AP** and select `AP_A057FXXU...tar.md5`.
   - Click **CP** and select `CP_A057FXXU...tar.md5`.
   - Click **CSC** and select `CSC_...tar.md5`.
4. Under the **Options** tab in Odin, ensure only **Auto Reboot** and **F. Reset Time** are checked.
5. Click **Start**. The flashing process will write all partitions to the internal UFS/eMMC storage.
6. Once completed, Odin will display a green **PASS!** box and the phone will automatically reboot into Samsung One UI.

---

## 4. Emergency Recovery via Custom Recovery (OrangeFox / TWRP)

If you have OrangeFox Recovery or TWRP installed on the recovery partition:

### Restoring Stock Boot Partition
If you want to quickly restore only the stock Android boot partition without wiping your system:
```bash
adb push stock_boot.img /tmp/boot.img
adb shell "dd if=/tmp/boot.img of=/dev/block/by-name/boot"
adb reboot
```

### Re-formatting Userdata to EXT4 / F2FS
If you previously formatted `userdata` (`/dev/block/by-name/userdata` or `/dev/block/sda37`) to Apple HFS+:
1. Boot into OrangeFox Recovery (Power + Volume Up).
2. Go to **Wipe** &rarr; **Format Data** &rarr; Type `yes`.
3. OrangeFox will re-create the native Android EXT4 / F2FS filesystem, allowing stock Android to boot normally.
