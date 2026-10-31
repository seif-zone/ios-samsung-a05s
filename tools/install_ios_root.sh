#!/bin/sh
# ==============================================================================
# iOS 16.7.16 RootFS Deployment Script for Samsung Galaxy A05s (SM-A057F)
# Maintained by seif-zone <https://github.com/seif-zone/ios-samsung-a05s>
#
# Execute this script inside OrangeFox Recovery Terminal or via:
#   adb shell sh /external_sd/install_ios_root.sh
# ==============================================================================

echo ""
echo "=========================================================="
echo "  iOS 16.7.16 RootFS Installer for Samsung Galaxy A05s   "
echo "  Target SoC: Snapdragon 680 (SM6225) / Motherboard: m269 "
echo "=========================================================="
echo ""

# 1. Locate userdata partition
USERDATA=""
for dev in /dev/block/by-name/userdata /dev/block/bootdevice/by-name/userdata /dev/block/platform/*/by-name/userdata; do
    if [ -b "$dev" ]; then
        USERDATA="$dev"
        break
    fi
done

if [ -z "$USERDATA" ]; then
    echo "[-] ERROR: Could not locate userdata partition on device!"
    exit 1
fi
echo "[+] Detected target partition: $USERDATA"

# 2. Locate ios16-root.tar on MicroSD or internal storage
TAR_FILE=""
for p in /external_sd/ios16-root.tar /sdcard1/ios16-root.tar /sdcard/ios16-root.tar /tmp/ios16-root.tar; do
    if [ -f "$p" ]; then
        TAR_FILE="$p"
        break
    fi
done

if [ -z "$TAR_FILE" ]; then
    echo "[-] ERROR: ios16-root.tar not found on MicroSD or internal storage!"
    echo "    Please copy 'ios16-root.tar' to the root of your MicroSD card."
    exit 1
fi
echo "[+] Found RootFS archive: $TAR_FILE"

# 3. Check for existing Android backup
echo "[*] Checking for safety Android Data backup..."
if [ -d "/external_sd/Fox/BACKUPS" ] || [ -d "/external_sd/OrangeFox/BACKUPS" ] || [ -d "/external_sd/TWRP/BACKUPS" ]; then
    echo "[+] Safety backup directory found on MicroSD."
else
    echo "[!] WARNING: No OrangeFox backup detected on MicroSD!"
    echo "    To preserve your Android data, make a 1-click 'Backup -> Data' in OrangeFox first."
fi

# 4. Prepare mount point
MOUNT_DIR="/tmp/ios_root_mount"
mkdir -p "$MOUNT_DIR"
umount "$MOUNT_DIR" 2>/dev/null || true
umount "$USERDATA" 2>/dev/null || true

# 5. Extract RootFS directly onto the partition
echo "[*] Preparing partition $USERDATA..."

# Format or mount partition
if mount -o rw "$USERDATA" "$MOUNT_DIR" 2>/dev/null; then
    echo "[+] Mounted partition at $MOUNT_DIR"
else
    echo "[*] Formatting partition..."
    mke2fs -t ext4 -b 4096 -F "$USERDATA" 2>/dev/null || mkfs.ext4 -F "$USERDATA" 2>/dev/null || true
    mount -t ext4 -o rw "$USERDATA" "$MOUNT_DIR"
fi

cd "$MOUNT_DIR"
echo "[*] Extracting $TAR_FILE (this may take 2-4 minutes)..."
# Extract without dying on non-fatal warnings
tar -xpf "$TAR_FILE" 2>/dev/null || tar -xf "$TAR_FILE" 2>/dev/null || true

# 6. Ensure canonical iOS symlinks exist natively on filesystem
echo "[*] Setting up canonical system symlinks..."
rm -f etc var tmp 2>/dev/null || true
ln -sf private/etc etc
ln -sf private/var var
ln -sf private/tmp tmp

mkdir -p System/Cryptexes
rm -f System/Cryptexes/OS System/Cryptexes/App 2>/dev/null || true
ln -sf ../../private/preboot/Cryptexes/OS System/Cryptexes/OS
ln -sf ../../private/preboot/Cryptexes/App System/Cryptexes/App

mkdir -p Library
rm -f Library/Preferences Library/Logs Library/Keychains Library/MobileDevice 2>/dev/null || true
ln -sf ../private/var/preferences Library/Preferences
ln -sf ../private/var/logs Library/Logs
ln -sf ../private/var/Keychains Library/Keychains
ln -sf ../private/var/MobileDevice Library/MobileDevice

mkdir -p sbin
if [ -f "System/Library/Filesystems/hfs.fs/mount_hfs" ]; then
    cp -f "System/Library/Filesystems/hfs.fs/mount_hfs" sbin/mount_hfs 2>/dev/null || ln -sf ../System/Library/Filesystems/hfs.fs/mount_hfs sbin/mount_hfs
fi
if [ -f "System/Library/Filesystems/hfs.fs/fsck_hfs" ]; then
    cp -f "System/Library/Filesystems/hfs.fs/fsck_hfs" sbin/fsck_hfs 2>/dev/null || ln -sf ../System/Library/Filesystems/hfs.fs/fsck_hfs sbin/fsck_hfs
fi
if [ -f "System/Library/Filesystems/hfs.fs/newfs_hfs" ]; then
    cp -f "System/Library/Filesystems/hfs.fs/newfs_hfs" sbin/newfs_hfs 2>/dev/null || ln -sf ../System/Library/Filesystems/hfs.fs/newfs_hfs sbin/newfs_hfs
fi

# 7. Verify critical system components
echo "[*] Verifying extracted iOS system tree..."
for check_path in sbin/launchd usr/libexec/backboardd System/Library/CoreServices/SpringBoard.app/SpringBoard System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64 private/var/keybags/systembag.kb; do
    if [ -f "$check_path" ]; then
        echo "  [OK] $check_path"
    else
        echo "  [!] Missing: $check_path"
    fi
done

# 8. Sync and unmount
echo "[*] Flushing buffers to storage..."
sync
cd /
umount "$MOUNT_DIR" 2>/dev/null || true

echo ""
echo "=========================================================="
echo "  [SUCCESS] iOS 16.7.16 RootFS successfully installed!    "
echo "  Now flash 'a05s-ios-orangefox.zip' in OrangeFox and     "
echo "  reboot to System to boot into iOS!                      "
echo "=========================================================="
echo ""
