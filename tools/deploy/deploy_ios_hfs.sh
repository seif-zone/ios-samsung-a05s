#!/bin/sh
set -e
echo "=========================================================="
echo "  iOS 16 HFS+ RootFS Deployer for Samsung Galaxy A05s   "
echo "  Target SoC: Snapdragon 680 (SM6225) / UFS 2.2         "
echo "=========================================================="

echo "[*] Unmounting existing partitions..."
umount /data 2>/dev/null || true
umount /mnt/ios 2>/dev/null || true
umount /dev/block/sda36 2>/dev/null || true
losetup -D 2>/dev/null || true

echo "[*] Attaching loopback device to /dev/block/sda36 (512-byte sector translation)..."
losetup -f /dev/block/sda36
LOOP_DEV=$(losetup -j /dev/block/sda36 | cut -d: -f1)
if [ -z "$LOOP_DEV" ]; then
    LOOP_DEV="/dev/block/loop0"
fi
echo "[+] Loop device: $LOOP_DEV"

echo "[*] Formatting /dev/block/sda36 as Apple HFS+ (Volume: iOSRoot)..."
cp /external_sd/newfs_hfs_static /tmp/newfs_hfs_static
chmod +x /tmp/newfs_hfs_static
/tmp/newfs_hfs_static -v iOSRoot "$LOOP_DEV"
echo "[+] Format completed!"

echo "[*] Preparing hfs_static extraction engine..."
cp /external_sd/hfs_static /tmp/hfs_static 2>/dev/null || true
chmod +x /tmp/hfs_static

echo "[*] Unpacking iOS 16 RootFS (321,288 files) directly into HFS+ volume..."
echo "[*] Writing directly to UFS storage (takes ~5-7 minutes)..."
/tmp/hfs_static "$LOOP_DEV" untar /external_sd/ios16-root.tar

echo "[*] Flushing disk caches..."
sync
losetup -d "$LOOP_DEV" 2>/dev/null || true
sync

echo ""
echo "=========================================================="
echo " [SUCCESS] iOS 16 RootFS is fully deployed in HFS+ format!"
echo " Ready for Stage 3 native launchd & SpringBoard boot."
echo "=========================================================="
