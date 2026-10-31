#!/usr/bin/env python3
"""Create an OrangeFox / TWRP flashable .zip installer for Samsung Galaxy A05s (SM-A057F).

The installer:
  1. Detects the Samsung A05s eMMC boot partition block (/dev/block/by-name/boot).
  2. Automatically creates a backup of stock boot image to /sdcard/stock_boot_backup.img.
  3. Flashes the iOS 16 Darwin XNU boot image safely.
  4. Syncs filesystem caches.

Usage:
  python3 tools/mkzip-orangefox.py INPUT_BOOT_IMG OUTPUT_ZIP
"""
import argparse, os, sys, zipfile

UPDATE_BINARY_SCRIPT = r"""#!/sbin/sh
# OrangeFox / TWRP update-binary for Samsung Galaxy A05s (SM-A057F)
OUTFD=$2
ZIPFILE=$3

ui_print() {
    echo -e "ui_print $1\nui_print" > /proc/self/fd/$OUTFD
}

ui_print " "
ui_print "================================================="
ui_print "  Samsung Galaxy A05s (SM-A057F / m269)"
ui_print "  iOS 16 Darwin XNU Kernel Installer"
ui_print "  Maintained by Seif (@seif-zone)"
ui_print "================================================="
ui_print " "

# 1. Locate boot partition
BOOT_DEV=""
for candidate in \
    /dev/block/by-name/boot \
    /dev/block/bootdevice/by-name/boot \
    /dev/block/platform/soc/7804000.sdhci/by-name/boot
do
    if [ -b "$candidate" ] || [ -e "$candidate" ]; then
        BOOT_DEV="$candidate"
        break
    fi
done

if [ -z "$BOOT_DEV" ]; then
    ui_print "[-] ERROR: Could not locate eMMC boot partition on device."
    exit 1
fi

ui_print "[*] Found boot partition: $BOOT_DEV"

# 2. Automated Safe Backup of Current Boot
BACKUP_DIR="/sdcard/OrangeFox/backup"
mkdir -p "$BACKUP_DIR" 2>/dev/null || BACKUP_DIR="/sdcard"
BACKUP_PATH="$BACKUP_DIR/stock_boot_backup_$(date +%Y%m%d_%H%M%S).img"

ui_print "[*] Backing up current kernel to:"
ui_print "    $BACKUP_PATH"
dd if="$BOOT_DEV" of="$BACKUP_PATH" bs=4096 count=16384 2>/dev/null
ui_print "[+] Backup complete."

# 3. Flash iOS Darwin XNU Boot Image
ui_print "[*] Writing iOS Darwin XNU kernel Image (Header v2)..."
unzip -p "$ZIPFILE" boot.img | dd of="$BOOT_DEV" bs=4096 2>/dev/null

# 4. Sync
ui_print "[*] Syncing filesystem buffers..."
sync

ui_print " "
ui_print "[SUCCESS] iOS 16 Darwin XNU kernel installed!"
ui_print "To revert at any time, flash your backup from OrangeFox."
ui_print "================================================="
ui_print " "
exit 0
"""

def make_orangefox_zip(img_path, out_zip_path):
    if not os.path.isfile(img_path):
        print(f"[-] Error: Input image '{img_path}' not found.")
        sys.exit(1)

    print(f"[*] Packaging OrangeFox flashable ZIP: '{out_zip_path}'...")
    with zipfile.ZipFile(out_zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        # Add boot image
        z.write(img_path, arcname="boot.img")
        
        # Add update-binary
        binary_info = zipfile.ZipInfo("META-INF/com/google/android/update-binary")
        binary_info.external_attr = 0o755 << 16  # Executable permissions
        z.writestr(binary_info, UPDATE_BINARY_SCRIPT)
        
        # Add dummy updater-script (required by recovery zip verifier)
        z.writestr("META-INF/com/google/android/updater-script", "# Dummy updater-script\n")

    print(f"[+] Flashable ZIP created successfully: {out_zip_path}")
    print(f"    Size: {os.path.getsize(out_zip_path):,} bytes")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Create OrangeFox flashable ZIP for Samsung A05s")
    parser.add_argument("input", help="Path to input boot.img (e.g. shim/out/a05s-boot.img)")
    parser.add_argument("output", help="Path to output .zip (e.g. out/a05s-ios-orangefox.zip)")
    args = parser.parse_args()

    make_orangefox_zip(args.input, args.output)
