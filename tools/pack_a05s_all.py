#!/usr/bin/env python3
"""Complete standalone build & packaging pipeline for Samsung Galaxy A05s (SM-A057F / m269).
Produces:
  1. a05s-boot.img (Android Boot Image Header Version 2 for fastboot / OrangeFox)
  2. a05s-boot.tar.md5 (Samsung Odin / Download Mode)
  3. a05s-ios-orangefox.zip (Flashable ZIP for OrangeFox Recovery)
"""
import hashlib, os, struct, sys, tarfile, zipfile

def pad_to(data, size):
    rem = len(data) % size
    if rem != 0:
        data += b'\x00' * (size - rem)
    return data

def build_boot_img_v2(kernel_data, ramdisk_data, cmdline, out_path):
    PAGE_SIZE = 4096
    ks = len(kernel_data)
    ka = 0x00008000
    rs = len(ramdisk_data)
    ra = 0x04000000
    ss = 0
    sa = 0
    ta = 0x00000100
    ps = PAGE_SIZE
    ver = 2
    # Android 13: (13 << 25) | (2025 << 4) | 1
    os_ver = (13 << 25) | (0 << 18) | (2025 << 4) | 1
    name = b"m269_sweet_xnu\x00"

    # Compute SHA1
    h = hashlib.sha1()
    h.update(kernel_data)
    h.update(struct.pack('<I', ks))
    h.update(ramdisk_data)
    h.update(struct.pack('<I', rs))
    h.update(b'')
    h.update(struct.pack('<I', 0))
    # for v2, dtb if any
    h.update(b'')
    h.update(struct.pack('<I', 0))
    img_id = h.digest()
    img_id = img_id.ljust(32, b'\x00')

    cmdline_bytes = cmdline.encode('ascii')
    cmd1 = cmdline_bytes[:512].ljust(512, b'\x00')
    cmd2 = cmdline_bytes[512:1536].ljust(1024, b'\x00')

    # Header v0 (first 608 bytes)
    hdr = bytearray()
    hdr += b'ANDROID!'                                           # 0x000: magic
    hdr += struct.pack('<10I', ks, ka, rs, ra, ss, sa, ta, ps, ver, os_ver) # 0x008: 40 bytes
    hdr += name.ljust(16, b'\x00')                               # 0x030: 16 bytes
    hdr += cmd1                                                  # 0x040: 512 bytes
    hdr += img_id                                                # 0x240: 32 bytes
    hdr += cmd2                                                  # 0x260: 1024 bytes
    
    # Header v1 fields (16 bytes at 0x660)
    # recovery_dtbo_size (u32), recovery_dtbo_offset (u64), header_size (u32)
    hdr += struct.pack('<IQI', 0, 0, 1664)

    # Header v2 fields (12 bytes at 0x670)
    # dtb_size (u32), dtb_addr (u64)
    hdr += struct.pack('<IQ', 0, 0)

    # Pad header to page size
    hdr = pad_to(hdr, PAGE_SIZE)
    kernel_padded = pad_to(bytearray(kernel_data), PAGE_SIZE)
    ramdisk_padded = pad_to(bytearray(ramdisk_data), PAGE_SIZE)

    with open(out_path, 'wb') as f:
        f.write(hdr)
        f.write(kernel_padded)
        f.write(ramdisk_padded)

    print(f"[+] Successfully wrote Boot Image v2 to {out_path} ({os.path.getsize(out_path):,} bytes)")

def build_odin_tar_md5(img_path, out_tar_path):
    with tarfile.open(out_tar_path, mode="w") as tar:
        tar.add(img_path, arcname="boot.img")
    
    with open(out_tar_path, "rb") as f:
        data = f.read()
        digest = hashlib.md5(data).hexdigest()
    
    tar_md5_path = out_tar_path + ".md5" if not out_tar_path.endswith(".md5") else out_tar_path
    base_name = os.path.basename(out_tar_path)
    with open(tar_md5_path, "wb") as f:
        f.write(data)
        f.write(f"\n{digest}  {base_name}\n".encode('ascii'))
    
    print(f"[+] Successfully generated Odin package: {tar_md5_path} ({os.path.getsize(tar_md5_path):,} bytes)")

def build_orangefox_zip(img_path, out_zip_path):
    from mkzip_orangefox_script import UPDATE_BINARY_SCRIPT
    with zipfile.ZipFile(out_zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.write(img_path, arcname="boot.img")
        binary_info = zipfile.ZipInfo("META-INF/com/google/android/update-binary")
        binary_info.external_attr = 0o755 << 16
        z.writestr(binary_info, UPDATE_BINARY_SCRIPT)
        z.writestr("META-INF/com/google/android/updater-script", "# OrangeFox Installer\n")
    print(f"[+] Successfully generated OrangeFox ZIP: {out_zip_path} ({os.path.getsize(out_zip_path):,} bytes)")

def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    shim_img = os.path.join(root, "shim", "out", "Image")
    payload_path = os.path.join(root, "out", "a05s.payload")
    out_dir = os.path.join(root, "out")
    os.makedirs(out_dir, exist_ok=True)

    if not os.path.isfile(shim_img):
        print(f"[-] Error: {shim_img} not found. Please compile the shim first.")
        sys.exit(1)
    if not os.path.isfile(payload_path):
        print(f"[-] Error: {payload_path} not found.")
        sys.exit(1)

    print("[*] Reading shim Image and XNU payload...")
    with open(shim_img, "rb") as f:
        shim_bytes = bytearray(f.read())
    
    # Read image_size from offset 16
    orig_size = struct.unpack('<Q', shim_bytes[16:24])[0]
    print(f"[*] Base shim size: {len(shim_bytes)} bytes, image_size: {orig_size:#x}")

    # Pad shim to original image_size
    if len(shim_bytes) < orig_size:
        shim_bytes += b'\x00' * (orig_size - len(shim_bytes))
    
    # Align to 4K page
    shim_bytes = pad_to(shim_bytes, 4096)

    # Append XNU payload
    with open(payload_path, "rb") as f:
        payload_bytes = f.read()

    combined_kernel = shim_bytes + payload_bytes
    # Update total size at offset 16
    total_kernel_size = len(combined_kernel)
    struct.pack_into('<Q', combined_kernel, 16, total_kernel_size)
    print(f"[+] Combined Kernel Image size: {total_kernel_size:,} bytes ({total_kernel_size / (1024*1024):.2f} MB)")

    # Minimal empty cpio ramdisk
    ramdisk_bytes = b'07070100000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000b00000000TRAILER!!!\x00\x00\x00\x00'

    cmdline = "console=null earlycon=msm_geni_serial,0x4a90000 sweetfb_console=1 cpus=4 debug=0x14e rd=md0 phys_base=0xb0000000"

    boot_img_path = os.path.join(out_dir, "a05s-boot.img")
    build_boot_img_v2(combined_kernel, ramdisk_bytes, cmdline, boot_img_path)

    # Build Odin tar.md5
    odin_tar_path = os.path.join(out_dir, "a05s-boot.tar.md5")
    build_odin_tar_md5(boot_img_path, odin_tar_path)

    # Build OrangeFox ZIP
    fox_zip_path = os.path.join(out_dir, "a05s-ios-orangefox.zip")
    with open(os.path.join(root, "tools", "mkzip-orangefox.py"), "r", encoding="utf-8") as f:
        lines = f.read()
    start_token = "UPDATE_BINARY_SCRIPT = r\"\"\""
    idx = lines.find(start_token)
    end_idx = lines.find('"""', idx + len(start_token))
    script_content = lines[idx + len(start_token):end_idx]
    
    with zipfile.ZipFile(fox_zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.write(boot_img_path, arcname="boot.img")
        binary_info = zipfile.ZipInfo("META-INF/com/google/android/update-binary")
        binary_info.external_attr = 0o755 << 16
        z.writestr(binary_info, script_content)
        z.writestr("META-INF/com/google/android/updater-script", "# OrangeFox Installer\n")
    print(f"[+] Successfully generated OrangeFox ZIP: {fox_zip_path} ({os.path.getsize(fox_zip_path):,} bytes)")

if __name__ == '__main__':
    main()
