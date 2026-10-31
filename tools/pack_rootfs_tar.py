#!/usr/bin/env python3
"""Package the prepared iOS 16 RootFS into a standard POSIX tar archive
with exact Unix UIDs, GIDs, file modes, and symbolic links.
"""
import os
import stat
import sys
import tarfile

ROOT = r'D:\.gemini\antigravity\scratch\rootfs_build\os_root'
OUT_TAR = r'D:\.gemini\antigravity\scratch\ios16-root.tar'

# Known Unix symlinks in the iOS RootFS
SYMLINKS = {
    'etc': 'private/etc',
    'var': 'private/var',
    'tmp': 'private/tmp',
    'System/Cryptexes/OS': '../../private/preboot/Cryptexes/OS',
    'System/Cryptexes/App': '../../private/preboot/Cryptexes/App',
    'Library/Preferences': '../private/var/preferences',
    'Library/Logs': '../private/var/logs',
    'Library/Keychains': '../private/var/Keychains',
    'Library/MobileDevice': '../private/var/MobileDevice',
    'sbin/mount_hfs': '../System/Library/Filesystems/hfs.fs/mount_hfs',
    'sbin/fsck_hfs': '../System/Library/Filesystems/hfs.fs/fsck_hfs',
    'sbin/newfs_hfs': '../System/Library/Filesystems/hfs.fs/newfs_hfs',
}


def get_posix_attr(rel_path, is_dir):
    """Determine correct POSIX owner and mode for each path."""
    rel_norm = rel_path.replace('\\', '/')

    # Defaults
    uid, gid = 0, 0
    uname, gname = 'root', 'wheel'
    mode = 0o755 if is_dir else 0o644

    # Mobile user paths (501:501)
    if rel_norm.startswith('private/var/mobile') or 'data_ark.plist' in rel_norm:
        uid, gid = 501, 501
        uname, gname = 'mobile', 'mobile'
        mode = 0o755 if is_dir else 0o600

    # Logd paths (272:272)
    elif 'private/var/db/diagnostics' in rel_norm or 'private/var/db/uuidtext' in rel_norm:
        uid, gid = 272, 272
        uname, gname = '_logd', '_logd'
        mode = 0o751 if is_dir else 0o644

    # Keybags (0700 dir, 0600 file)
    elif 'private/var/keybags' in rel_norm:
        mode = 0o700 if is_dir else 0o600

    # Executables
    elif any(rel_norm.startswith(p) for p in ['bin/', 'sbin/', 'usr/bin/', 'usr/sbin/', 'usr/libexec/']) or \
         rel_norm.endswith('.dylib') or \
         rel_norm.endswith('.app/SpringBoard') or \
         'SpringBoard.app' in rel_norm and not rel_norm.endswith('.plist'):
        if not is_dir:
            mode = 0o755

    return uid, gid, uname, gname, mode


def main():
    print(f'Creating POSIX archive: {OUT_TAR}')
    count = 0

    with tarfile.open(OUT_TAR, 'w') as tar:
        # First, register explicitly defined symlinks
        for link_path, target in SYMLINKS.items():
            ti = tarfile.TarInfo(name=link_path)
            ti.type = tarfile.SYMTYPE
            ti.linkname = target
            ti.uid, ti.gid, ti.uname, ti.gname, ti.mode = get_posix_attr(link_path, False)
            tar.addfile(ti)
            print(f'  Added symlink: {link_path} -> {target}')

        # Walk directory
        for dirpath, dirnames, filenames in os.walk(ROOT):
            rel_dir = os.path.relpath(dirpath, ROOT)
            if rel_dir == '.':
                rel_dir = ''

            # Skip symlink directories we already handled
            norm_rel_dir = rel_dir.replace('\\', '/')
            if norm_rel_dir in SYMLINKS:
                continue

            # Add directory itself if not root
            if rel_dir:
                di = tarfile.TarInfo(name=norm_rel_dir)
                di.type = tarfile.DIRTYPE
                di.uid, di.gid, di.uname, di.gname, di.mode = get_posix_attr(rel_dir, True)
                tar.addfile(di)

            for fn in filenames:
                full_fn = os.path.join(dirpath, fn)
                rel_file = os.path.join(rel_dir, fn) if rel_dir else fn
                norm_rel_file = rel_file.replace('\\', '/')

                # Skip files replaced by symlinks
                if norm_rel_file in SYMLINKS:
                    continue

                ti = tarfile.TarInfo(name=norm_rel_file)
                ti.size = os.path.getsize(full_fn)
                ti.mtime = int(os.path.getmtime(full_fn))
                ti.uid, ti.gid, ti.uname, ti.gname, ti.mode = get_posix_attr(rel_file, False)

                try:
                    with open(full_fn, 'rb') as f:
                        tar.addfile(ti, f)
                    count += 1
                    if count % 10000 == 0:
                        print(f'  Archived {count} files...')
                except Exception as e:
                    print(f'  Warning: Skipping {rel_file}: {e}')

    print(f'Done! Successfully archived {count} files into {OUT_TAR}')
    size_gb = os.path.getsize(OUT_TAR) / (1024**3)
    print(f'Final archive size: {size_gb:.2f} GB')


if __name__ == '__main__':
    main()
