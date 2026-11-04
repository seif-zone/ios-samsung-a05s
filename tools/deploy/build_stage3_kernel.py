#!/usr/bin/env python3
"""Build and package Darwin XNU Stage 3 Boot Image and Odin TAR for Samsung Galaxy A05s.
Usage:
    python3 tools/deploy/build_stage3_kernel.py [--kernel PATH] [--adt PATH] [--out PATH]
"""
import os, sys, struct, tarfile, hashlib, argparse

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(REPO_ROOT, 'tools'))

import mkpayload
import pack_a05s_all

DEFAULT_CMDLINE = (
    'debug=0xc serial=3 cpus=1 keepsyms=1 -noprogress rd=ufsroot0 '
    'use_ufs=1 noufs=0 unentitled_ios_sim_launch=1 ignition_level=1 '
    'wdt_test=no_user_checkin ufsrw=1 rootrw=1 launchd_unsecure_cache=1 '
    'wdt=-1 sweetfb_hz=60 sweetfb_stayon=1'
)

def parse_args():
    parser = argparse.ArgumentParser(description="Build Stage 3 Boot Image & Odin Package for Samsung A05s")
    parser.add_argument('--kernel', default=os.path.join(REPO_ROOT, 'out', 'artifacts', 'xnu-kernel', 'kernel.development.sweet'), help="Path to Mach-O kernel")
    parser.add_argument('--adt', default=os.path.join(REPO_ROOT, 'out', 'a05s.adt'), help="Path to Apple Device Tree (ADT)")
    parser.add_argument('--shim', default=os.path.join(REPO_ROOT, 'shim', 'out', 'Image'), help="Path to shim Image binary")
    parser.add_argument('--cmdline', default=DEFAULT_CMDLINE, help="Boot arguments")
    parser.add_argument('--out-boot', default=os.path.join(REPO_ROOT, 'out', 'a05s-stage3-boot.img'), help="Output boot.img path")
    parser.add_argument('--out-tar', default=os.path.join(REPO_ROOT, 'out', 'AP_A05s_iOS16_Stage3_GUI.tar.md5'), help="Output Odin tar.md5 path")
    parser.add_argument('--vbmeta', default=os.path.join(REPO_ROOT, 'out', 'vbmeta.img'), help="Path to disabled vbmeta.img")
    return parser.parse_args()

def main():
    args = parse_args()
    os.makedirs(os.path.dirname(args.out_boot), exist_ok=True)
    os.makedirs(os.path.dirname(args.out_tar), exist_ok=True)

    payload_path = os.path.join(REPO_ROOT, 'out', 'a05s_stage3.payload')

    print('[1/4] Packing Mach-O kernel + ADT into Stage 3 payload...')
    blob, info = mkpayload.build(args.kernel, args.adt, args.cmdline, None)
    with open(payload_path, 'wb') as f:
        f.write(blob)
    print(f'[+] Created {payload_path} ({len(blob):,} bytes)')

    print('[2/4] Reading shim Image and combining with Stage 3 payload...')
    with open(args.shim, 'rb') as f:
        shim_bytes = bytearray(f.read())

    orig_size = struct.unpack('<Q', shim_bytes[16:24])[0]
    if len(shim_bytes) < orig_size:
        shim_bytes += b'\x00' * (orig_size - len(shim_bytes))

    shim_bytes = pack_a05s_all.pad_to(shim_bytes, 4096)
    with open(payload_path, 'rb') as f:
        payload_bytes = f.read()

    combined_kernel = shim_bytes + payload_bytes
    total_kernel_size = len(combined_kernel)
    struct.pack_into('<Q', combined_kernel, 16, total_kernel_size)

    ramdisk_bytes = b'07070100000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000b00000000TRAILER!!!\x00\x00\x00\x00'

    print('[3/4] Building Android Boot Image Header v4 (Header v2/v4 compatible)...')
    pack_a05s_all.build_boot_img_v4(combined_kernel, ramdisk_bytes, args.out_boot, os_version=0x1a0001a8)
    print(f'[+] Generated {args.out_boot} ({os.path.getsize(args.out_boot):,} bytes)')

    print('[4/4] Generating Odin Tar.MD5 Package (USTAR + disabled vbmeta)...')
    raw_tar = args.out_tar[:-4] if args.out_tar.endswith('.md5') else args.out_tar + '.tmp'

    with tarfile.open(raw_tar, mode='w', format=tarfile.USTAR_FORMAT) as tar:
        ti_boot = tar.gettarinfo(args.out_boot, arcname='boot.img')
        ti_boot.uname = ''
        ti_boot.gname = ''
        ti_boot.uid = 0
        ti_boot.gid = 0
        ti_boot.mode = 0o666
        with open(args.out_boot, 'rb') as f:
            tar.addfile(ti_boot, f)

        if os.path.exists(args.vbmeta):
            ti_vbmeta = tar.gettarinfo(args.vbmeta, arcname='vbmeta.img')
            ti_vbmeta.uname = ''
            ti_vbmeta.gname = ''
            ti_vbmeta.uid = 0
            ti_vbmeta.gid = 0
            ti_vbmeta.mode = 0o666
            with open(args.vbmeta, 'rb') as f:
                tar.addfile(ti_vbmeta, f)

    with open(raw_tar, 'rb') as f:
        data = f.read()
        digest = hashlib.md5(data).hexdigest()

    base_tar_name = os.path.basename(args.out_tar[:-4] if args.out_tar.endswith('.md5') else args.out_tar)
    trailer = f'{digest}  {base_tar_name}\n'.encode('ascii')
    with open(args.out_tar, 'wb') as f:
        f.write(data)
        f.write(trailer)

    if os.path.exists(raw_tar):
        os.remove(raw_tar)

    print(f'[SUCCESS] Generated Odin flash package: {args.out_tar} ({os.path.getsize(args.out_tar):,} bytes)')

if __name__ == '__main__':
    main()
