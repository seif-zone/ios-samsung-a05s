#!/usr/bin/env python3
"""Extract missing files from SystemOS and AppOS cryptexes using dissect.apfs
and ensure all trampoline libraries and root counterparts are in place.
"""
import os, sys, argparse
import dissect.apfs

def parse_args():
    parser = argparse.ArgumentParser(description="Extract missing files from SystemOS and AppOS cryptexes into rootfs.")
    parser.add_argument("--root", default=os.environ.get("IOS_ROOTFS", "rootfs_build/os_root"), help="Path to unpacked rootfs directory")
    parser.add_argument("--sysos", default=os.environ.get("SYSOS_DMG", "087-86593-047.dmg"), help="Path to SystemOS cryptex dmg")
    parser.add_argument("--appos", default=os.environ.get("APPOS_DMG", "087-86715-047.dmg"), help="Path to AppOS cryptex dmg")
    return parser.parse_args()


def extract_volume(dmg_path, target_cryptex_dir, c_name):
    print(f'Extracting missing files from {c_name} cryptex...')
    extracted_count = 0
    with open(dmg_path, 'rb') as f:
        apfs = dissect.apfs.APFS(f)
        vol = apfs.volumes[0]

        def walk(entry, rel_path):
            nonlocal extracted_count
            if entry.is_dir():
                for child in entry.inode.iterdir():
                    child_rel = os.path.join(rel_path, child.name) if rel_path else child.name
                    walk(child, child_rel)
            elif entry.is_file():
                dest_path = os.path.join(target_cryptex_dir, rel_path)
                # If file doesn't exist or is 0 bytes, extract it
                if not os.path.exists(dest_path) or os.path.getsize(dest_path) == 0:
                    try:
                        data = entry.inode.open().read()
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                        with open(dest_path, 'wb') as out_f:
                            out_f.write(data)
                        extracted_count += 1
                        if extracted_count <= 20 or extracted_count % 50 == 0:
                            print(f'  Extracted {rel_path} ({len(data)} bytes)')
                    except Exception as e:
                        print(f'  Failed to extract {rel_path}: {e}')

        for child in vol.root.iterdir():
            walk(child, child.name)

    print(f'Total {extracted_count} files extracted from {c_name}.')


def main():
    args = parse_args()
    root = os.path.abspath(args.root)
    os_target = os.path.join(root, 'private', 'preboot', 'Cryptexes', 'OS')
    app_target = os.path.join(root, 'private', 'preboot', 'Cryptexes', 'App')

    extract_volume(args.sysos, os_target, 'SystemOS')
    extract_volume(args.appos, app_target, 'AppOS')

    # Now link/copy cryptex trampolines to /usr/lib in the root
    trampolines = [
        ('usr/lib/libobjc-trampolines.dylib', 'usr/lib/libobjc-trampolines.dylib'),
        ('usr/lib/libffi-trampolines.dylib', 'usr/lib/libffi-trampolines.dylib'),
        ('usr/lib/libstdc++.6.0.9.dylib', 'usr/lib/libstdc++.6.0.9.dylib'),
        ('usr/lib/libstdc++.6.0.9.dylib', 'usr/lib/libstdc++.6.dylib'),
        ('usr/lib/libstdc++.6.0.9.dylib', 'usr/lib/libstdc++.dylib'),
    ]

    print('Copying essential runtime libraries to /usr/lib...')
    for src_rel, dst_rel in trampolines:
        src = os.path.join(os_target, src_rel.replace('/', os.sep))
        dst = os.path.join(root, dst_rel.replace('/', os.sep))
        if os.path.exists(src) and os.path.getsize(src) > 0:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(src, 'rb') as f_in, open(dst, 'wb') as f_out:
                f_out.write(f_in.read())
            print(f'  Copied {src_rel} -> {dst_rel} ({os.path.getsize(dst)} bytes)')
        else:
            print(f'  Warning: Source {src} not found or empty!')

    print('Cryptex processing complete!')


if __name__ == '__main__':
    main()
