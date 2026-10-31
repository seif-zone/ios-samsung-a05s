#!/usr/bin/env python3
"""Package Samsung A05s boot image into an Odin-compatible .tar / .tar.md5 archive.

Supports two modes:
  1. Boot mode (AP -> boot.img): Replaces standard boot kernel.
  2. Dual-Boot Recovery mode (AP -> recovery.img): Preserves stock Android completely.
     Normal power-on boots Android One UI; Power + Vol Up boots iOS Darwin XNU!

Usage:
  python3 tools/mktar-odin.py INPUT_IMG OUTPUT_TAR [--dualboot] [--md5]
"""
import argparse, hashlib, os, sys, tarfile

def package_odin(img_path, out_path, dualboot=False, add_md5=True):
    if not os.path.isfile(img_path):
        print(f"[-] Error: Input image '{img_path}' not found.")
        sys.exit(1)

    target_name = "recovery.img" if dualboot else "boot.img"
    base_tar = out_path if not add_md5 else (out_path[:-4] if out_path.endswith('.md5') else out_path)

    print(f"[*] Packaging '{img_path}' as '{target_name}' inside '{base_tar}'...")

    with tarfile.open(base_tar, mode="w") as tar:
        tar.add(img_path, arcname=target_name)

    final_path = base_tar
    if add_md5:
        md5_path = base_tar if base_tar.endswith('.tar.md5') else (base_tar + ".md5")
        print(f"[*] Computing MD5 signature for Odin verification...")
        with open(base_tar, "rb") as f:
            data = f.read()
            digest = hashlib.md5(data).hexdigest()
        
        # In Odin .tar.md5, the ASCII md5 string followed by two spaces and filename is appended at EOF
        tar_basename = os.path.basename(base_tar)
        with open(md5_path, "wb") as f:
            f.write(data)
            f.write(f"\n{digest}  {tar_basename}\n".encode('ascii'))
        
        if md5_path != base_tar and os.path.isfile(base_tar):
            os.remove(base_tar)
        final_path = md5_path

    print(f"[+] Successfully generated Odin package: {final_path}")
    print(f"    Mode: {'Dual-Boot (recovery partition)' if dualboot else 'Direct Boot (boot partition)'}")
    print(f"    Size: {os.path.getsize(final_path):,} bytes")
    return final_path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Create Odin .tar.md5 package for Samsung Galaxy A05s")
    parser.add_argument("input", help="Path to input boot.img (e.g. shim/out/a05s-boot.img)")
    parser.add_argument("output", help="Path to output .tar or .tar.md5")
    parser.add_argument("--dualboot", action="store_true", help="Package as recovery.img for safe Dual-Boot")
    parser.add_argument("--no-md5", action="store_true", help="Generate plain .tar without MD5 trailer")
    args = parser.parse_args()

    package_odin(args.input, args.output, dualboot=args.dualboot, add_md5=not args.no_md5)
