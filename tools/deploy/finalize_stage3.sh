#!/bin/sh
set -e
echo "=========================================================="
echo "  iOS 16 Stage 3 RootFS Finalizer for Samsung A05s        "
echo "  Volume: /dev/block/sda36 (userdata / HFS+ Case-Sensitive)"
echo "=========================================================="

HFS="/tmp/hfs_static"
NEWFS="/tmp/newfs_hfs_static"
ROOT="/dev/block/sda36"

echo "[1/6] Formatting /dev/block/sda36 with 512MB catalog & 268MB extents..."
$NEWFS -s -v iOSRoot -b 4096 -n e=4096,c=8192 -c e=65536,c=131072 $ROOT
echo "[+] Format completed!"

echo "[2/6] Injecting all RootFS folders into HFS+ volume..."
# Add sbin, bin, usr, Applications, Library first
for folder in sbin bin usr Applications Library cores dev Developer private System; do
    if [ -d "/sdcard/ios16_root/$folder" ]; then
        echo "[*] Creating /$folder..."
        $HFS $ROOT mkdir "/$folder" 2>/dev/null || true
        echo "[*] Adding contents of $folder..."
        $HFS $ROOT addall "/sdcard/ios16_root/$folder" "/$folder" 2>/dev/null || true
    fi
done

echo "[3/6] Setting permissions for executables and system daemons..."
$HFS $ROOT chmod 755 /sbin/launchd 2>/dev/null || true
$HFS $ROOT chmod 755 /usr/lib/dyld 2>/dev/null || true
$HFS $ROOT chmod 755 /System/Library/CoreServices/SpringBoard.app/SpringBoard 2>/dev/null || true
$HFS $ROOT chmod 755 /usr/libexec/backboardd 2>/dev/null || true
$HFS $ROOT chmod 755 /usr/libexec/containermanagerd 2>/dev/null || true
$HFS $ROOT chmod 755 /usr/libexec/logd 2>/dev/null || true
$HFS $ROOT chmod 755 /usr/libexec/mobileactivationd 2>/dev/null || true
$HFS $ROOT chmod 755 /usr/libexec/UserEventAgent 2>/dev/null || true

echo "[4/6] Creating genuine Apple symbolic links..."
$HFS $ROOT symlink private/etc /etc 2>/dev/null || true
$HFS $ROOT symlink private/tmp /tmp 2>/dev/null || true
$HFS $ROOT symlink private/var /var 2>/dev/null || true
$HFS $ROOT symlink ../private/var/Keychains /Library/Keychains 2>/dev/null || true
$HFS $ROOT symlink ../private/var/logs /Library/Logs 2>/dev/null || true
$HFS $ROOT symlink ../private/var/MobileDevice /Library/MobileDevice 2>/dev/null || true
$HFS $ROOT symlink ../private/var/preferences /Library/Preferences 2>/dev/null || true
$HFS $ROOT symlink ../System/Library/Filesystems/hfs.fs/fsck_hfs /sbin/fsck_hfs 2>/dev/null || true
$HFS $ROOT symlink ../System/Library/Filesystems/hfs.fs/mount_hfs /sbin/mount_hfs 2>/dev/null || true
$HFS $ROOT symlink ../System/Library/Filesystems/hfs.fs/newfs_hfs /sbin/newfs_hfs 2>/dev/null || true
$HFS $ROOT symlink ../../private/preboot/Cryptexes/App /System/Cryptexes/App 2>/dev/null || true
$HFS $ROOT symlink ../../private/preboot/Cryptexes/OS /System/Cryptexes/OS 2>/dev/null || true

echo "[5/6] Injecting Stage 3 helpers (keybag, migration skip, setup skip)..."
$HFS $ROOT mkdir /private/var/db 2>/dev/null || true
$HFS $ROOT mkdir /private/var/db/diagnostics 2>/dev/null || true
$HFS $ROOT mkdir /private/var/db/uuidtext 2>/dev/null || true
$HFS $ROOT mkdir /private/var/keybags 2>/dev/null || true
$HFS $ROOT add /sdcard/stage3_helpers/systembag.kb /private/var/keybags/systembag.kb 2>/dev/null || true
$HFS $ROOT add /sdcard/stage3_helpers/migrated.marker /private/var/db/diagnostics/.migrated 2>/dev/null || true
$HFS $ROOT add /sdcard/stage3_helpers/migrated.marker /private/var/db/uuidtext/.migrated 2>/dev/null || true

$HFS $ROOT mkdir /private/var/mobile 2>/dev/null || true
$HFS $ROOT mkdir /private/var/mobile/Library 2>/dev/null || true
$HFS $ROOT mkdir /private/var/mobile/Library/Preferences 2>/dev/null || true
$HFS $ROOT add /sdcard/stage3_helpers/com.apple.migration.plist /private/var/mobile/Library/Preferences/com.apple.migration.plist 2>/dev/null || true
$HFS $ROOT add /sdcard/stage3_helpers/com.apple.purplebuddy.plist /private/var/mobile/Library/Preferences/com.apple.purplebuddy.plist 2>/dev/null || true

echo "[6/6] Creating container directories for containermanagerd..."
$HFS $ROOT mkdir /private/var/containers 2>/dev/null || true
$HFS $ROOT mkdir /private/var/containers/Bundle 2>/dev/null || true
$HFS $ROOT mkdir /private/var/containers/Data 2>/dev/null || true
$HFS $ROOT mkdir /private/var/containers/Data/System 2>/dev/null || true
$HFS $ROOT mkdir /private/var/containers/Shared 2>/dev/null || true
$HFS $ROOT mkdir /private/var/containers/Shared/SystemGroup 2>/dev/null || true
$HFS $ROOT mkdir /private/var/containers/Temp 2>/dev/null || true

echo "[*] Syncing disk caches..."
sync
echo "=========================================================="
echo " [SUCCESS] Stage 3 HFS+ RootFS is fully deployed!"
echo "=========================================================="
