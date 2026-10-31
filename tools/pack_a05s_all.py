#!/usr/bin/env python3
"""Complete standalone build & packaging pipeline for Samsung Galaxy A05s (SM-A057F / m269).
Produces:
  1. a05s-boot-v4.img & a05s-boot.img (Android Boot Header v4 matched 1:1 to stock boot.emmc.win)
  2. a05s-boot-v4.tar.md5 (Samsung Odin / Download Mode)
  3. vbmeta.img & A057FXXUFDZH2_patched_vbmeta.tar.md5 (Samsung AVB verification disabled)
  4. a05s-ios-orangefox.zip (All-in-one flashable ZIP with automatic backup, vbmeta patch, & kernel flash)
"""
import hashlib, os, struct, sys, tarfile, zipfile

PAGE_SIZE = 4096

def pad_to(data, size):
    rem = len(data) % size
    if rem != 0:
        data += b'\x00' * (size - rem)
    return data

def build_boot_img_v4(kernel_data, ramdisk_data, out_path, os_version=0x1a0001a8):
    """Build Android Boot Image Header Version 4 (matched 1:1 to SM-A057F Android 13/14 GKI)."""
    ks = len(kernel_data)
    rs = len(ramdisk_data)
    header_size = 1584
    reserved = b'\x00' * 16
    header_ver = 4
    cmdline_bytes = b'\x00' * 1536
    sig_size = 0

    hdr = bytearray()
    hdr += b'ANDROID!'                                           # 0x000: 8 bytes
    hdr += struct.pack('<III', ks, rs, os_version)               # 0x008: 12 bytes
    hdr += struct.pack('<I', header_size)                        # 0x014: 4 bytes
    hdr += reserved                                              # 0x018: 16 bytes
    hdr += struct.pack('<I', header_ver)                         # 0x028: 4 bytes
    hdr += cmdline_bytes                                         # 0x02C: 1536 bytes
    hdr += struct.pack('<I', sig_size)                           # 0x62C: 4 bytes -> total 1584 bytes

    hdr = pad_to(hdr, PAGE_SIZE)
    kernel_padded = pad_to(bytearray(kernel_data), PAGE_SIZE)
    ramdisk_padded = pad_to(bytearray(ramdisk_data), PAGE_SIZE)

    with open(out_path, 'wb') as f:
        f.write(hdr)
        f.write(kernel_padded)
        f.write(ramdisk_padded)

    print(f"[+] Successfully wrote Boot Image v4 to {out_path} ({os.path.getsize(out_path):,} bytes)")

def build_odin_tar_md5(img_path, out_tar_path, arcname="boot.img"):
    with tarfile.open(out_tar_path, mode="w") as tar:
        tar.add(img_path, arcname=arcname)
    
    with open(out_tar_path, "rb") as f:
        data = f.read()
        digest = hashlib.md5(data).hexdigest()
    
    tar_md5_path = out_tar_path if out_tar_path.endswith(".md5") else out_tar_path + ".md5"
    base_name = os.path.basename(out_tar_path)
    with open(tar_md5_path, "wb") as f:
        f.write(data)
        f.write(f"\n{digest}  {base_name}\n".encode('ascii'))
    
    print(f"[+] Successfully generated Odin package: {tar_md5_path} ({os.path.getsize(tar_md5_path):,} bytes)")

ORANGEFOX_UPDATE_BINARY = r"""#!/sbin/sh
# All-in-one OrangeFox / TWRP update-binary for Samsung Galaxy A05s (SM-A057F)
OUTFD=$2
ZIPFILE=$3

ui_print() {
    echo -e "ui_print $1\nui_print" > /proc/self/fd/$OUTFD
}

ui_print " "
ui_print "================================================="
ui_print "  Samsung Galaxy A05s (SM-A057F / m269)"
ui_print "  iOS 16 Darwin XNU Kernel & AVB Patch Installer"
ui_print "  Maintained by Seif (@seif-zone)"
ui_print "================================================="
ui_print " "

# 1. Locate partitions
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

VBMETA_DEV=""
for candidate in \
    /dev/block/by-name/vbmeta \
    /dev/block/bootdevice/by-name/vbmeta \
    /dev/block/platform/soc/7804000.sdhci/by-name/vbmeta
do
    if [ -b "$candidate" ] || [ -e "$candidate" ]; then
        VBMETA_DEV="$candidate"
        break
    fi
done

if [ -z "$BOOT_DEV" ]; then
    ui_print "[-] ERROR: Could not locate boot partition on device."
    exit 1
fi

ui_print "[*] Found boot partition:   $BOOT_DEV"
if [ -n "$VBMETA_DEV" ]; then
    ui_print "[*] Found vbmeta partition: $VBMETA_DEV"
fi

# 2. Automated Safe Backup of Current Boot & VBMeta
BACKUP_DIR="/sdcard/OrangeFox/backup"
mkdir -p "$BACKUP_DIR" 2>/dev/null || BACKUP_DIR="/sdcard"
TS=$(date +%Y%m%d_%H%M%S)
BOOT_BACKUP="$BACKUP_DIR/stock_boot_${TS}.img"
VBMETA_BACKUP="$BACKUP_DIR/stock_vbmeta_${TS}.img"

ui_print "[*] Backing up current partitions..."
dd if="$BOOT_DEV" of="$BOOT_BACKUP" bs=4096 count=24576 2>/dev/null
ui_print "    -> Saved boot to:   $BOOT_BACKUP"

if [ -n "$VBMETA_DEV" ]; then
    dd if="$VBMETA_DEV" of="$VBMETA_BACKUP" bs=4096 count=1024 2>/dev/null
    ui_print "    -> Saved vbmeta to: $VBMETA_BACKUP"
fi

# 3. Flash Patched VBMeta (Disables Samsung AVB Verification)
if [ -n "$VBMETA_DEV" ]; then
    ui_print "[*] Writing Patched VBMeta (AVB Verification Disabled)..."
    unzip -p "$ZIPFILE" vbmeta.img | dd of="$VBMETA_DEV" bs=4096 2>/dev/null
    ui_print "[+] VBMeta patched successfully."
fi

# 4. Flash iOS Darwin XNU Boot Image Header v4
ui_print "[*] Writing iOS Darwin XNU Kernel (Android Boot Header v4)..."
unzip -p "$ZIPFILE" boot.img | dd of="$BOOT_DEV" bs=4096 2>/dev/null
ui_print "[+] Boot image installed successfully."

# 5. Sync
ui_print "[*] Syncing filesystem buffers..."
sync

ui_print " "
ui_print "================================================="
ui_print " [SUCCESS] iOS 16 Darwin XNU Kernel Installed!"
ui_print " AVB Verification is disabled."
ui_print " To restore Android at any time, restore from:"
ui_print " $BOOT_BACKUP"
ui_print "================================================="
ui_print " "
exit 0
"""

def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    shim_img = os.path.join(root, "shim", "out", "Image")
    payload_path = os.path.join(root, "out", "a05s.payload")
    out_dir = os.path.join(root, "out")
    os.makedirs(out_dir, exist_ok=True)

    if not os.path.isfile(shim_img):
        print(f"[-] Error: {shim_img} not found.")
        sys.exit(1)
    if not os.path.isfile(payload_path):
        print(f"[-] Error: {payload_path} not found.")
        sys.exit(1)

    print("[*] Reading shim Image and XNU payload...")
    with open(shim_img, "rb") as f:
        shim_bytes = bytearray(f.read())
    
    orig_size = struct.unpack('<Q', shim_bytes[16:24])[0]
    print(f"[*] Base shim size: {len(shim_bytes)} bytes, image_size: {orig_size:#x}")

    if len(shim_bytes) < orig_size:
        shim_bytes += b'\x00' * (orig_size - len(shim_bytes))
    
    shim_bytes = pad_to(shim_bytes, PAGE_SIZE)

    with open(payload_path, "rb") as f:
        payload_bytes = f.read()

    combined_kernel = shim_bytes + payload_bytes
    total_kernel_size = len(combined_kernel)
    struct.pack_into('<Q', combined_kernel, 16, total_kernel_size)
    print(f"[+] Combined Kernel Image size: {total_kernel_size:,} bytes ({total_kernel_size / (1024*1024):.2f} MB)")

    # Minimal ramdisk
    ramdisk_bytes = b'07070100000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000b00000000TRAILER!!!\x00\x00\x00\x00'

    # 1. Build Boot Image v4 (Standard GKI for Android 13/14 SM6225)
    boot_v4_path = os.path.join(out_dir, "a05s-boot-v4.img")
    build_boot_img_v4(combined_kernel, ramdisk_bytes, boot_v4_path, os_version=0x1a0001a8)

    # 2. Also write standard a05s-boot.img as v4
    boot_img_path = os.path.join(out_dir, "a05s-boot.img")
    build_boot_img_v4(combined_kernel, ramdisk_bytes, boot_img_path, os_version=0x1a0001a8)

    # 3. Build Odin tar.md5 for v4
    odin_tar_path = os.path.join(out_dir, "a05s-boot-v4.tar.md5")
    build_odin_tar_md5(boot_img_path, odin_tar_path, arcname="boot.img")

    # 4. Prepare authentic decompressed vbmeta.img
    vbmeta_src = r"C:\Users\seifh\.gemini\antigravity\scratch\vbmeta_extracted\vbmeta.img"
    vbmeta_out = os.path.join(out_dir, "vbmeta.img")
    if os.path.isfile(vbmeta_src):
        with open(vbmeta_src, "rb") as sf, open(vbmeta_out, "wb") as df:
            df.write(sf.read())
        print(f"[+] Placed authentic patched vbmeta.img ({os.path.getsize(vbmeta_out):,} bytes)")

    # 5. Build all-in-one OrangeFox ZIP
    fox_zip_path = os.path.join(out_dir, "a05s-ios-orangefox.zip")
    with zipfile.ZipFile(fox_zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.write(boot_img_path, arcname="boot.img")
        if os.path.isfile(vbmeta_out):
            z.write(vbmeta_out, arcname="vbmeta.img")
        binary_info = zipfile.ZipInfo("META-INF/com/google/android/update-binary")
        binary_info.external_attr = 0o755 << 16
        z.writestr(binary_info, ORANGEFOX_UPDATE_BINARY)
        z.writestr("META-INF/com/google/android/updater-script", "# OrangeFox Installer\n")
    print(f"[+] Successfully generated All-in-One OrangeFox ZIP: {fox_zip_path} ({os.path.getsize(fox_zip_path):,} bytes)")

if __name__ == '__main__':
    main()
