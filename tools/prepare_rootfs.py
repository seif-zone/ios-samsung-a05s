#!/usr/bin/env python3
"""Prepare the complete SWEET iOS 16 RootFS for Samsung Galaxy A05s (SM-A057F).
Applies all kernel/XNU and userspace tweaks required to reach SpringBoard.
"""
import glob
import os
import plistlib
import shutil
import sys

BUILD = '20H392'
VERSION = '16.7.16'
MOBILE_UID = 501
MOBILE_GID = 501


def load_plist(path):
    with open(path, 'rb') as f:
        return plistlib.load(f)


def save_plist(path, data, fmt=plistlib.FMT_BINARY):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        plistlib.dump(data, f, fmt=fmt)
    print(f'Saved plist: {os.path.basename(path)}')


def merge_pref(root, name, values):
    """Merge keys into /private/var/mobile/Library/Preferences/NAME.plist."""
    path = os.path.join(root, 'private', 'var', 'mobile', 'Library', 'Preferences', name + '.plist')
    data = load_plist(path) if os.path.exists(path) else {}
    data.update(values)
    save_plist(path, data)
    print(f'Preference updated: {name} -> {sorted(values.keys())}')


def setup_keybags_and_db(root):
    """Setup .migrated markers for logd and the plaintext system keybag for AppleKeyStore."""
    print('Setting up logd stores and system keybag...')
    for sub in ['diagnostics', 'uuidtext', os.path.join('diagnostics', 'timesync')]:
        p = os.path.join(root, 'private', 'var', 'db', sub)
        os.makedirs(p, exist_ok=True)
        migrated = os.path.join(p, '.migrated')
        with open(migrated, 'wb') as f:
            pass
        print(f'  Created {migrated}')

    kb_dir = os.path.join(root, 'private', 'var', 'keybags')
    os.makedirs(kb_dir, exist_ok=True)
    kb_path = os.path.join(kb_dir, 'systembag.kb')
    with open(kb_path, 'wb') as f:
        f.write(
            b'<?xml version="1.0" encoding="UTF-8"?>\n'
            b'<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            b'<plist version="1.0"><dict><key>KeyBagKeys</key><data>U1dFRVQ=</data></dict></plist>\n'
        )
    print(f'  Created {kb_path}')


def patch_launchd(root):
    """Patch launchd.plist to prevent kernel panics on daemon crashes and strip baseband."""
    print('Patching launchd.plist...')
    path = os.path.join(root, 'System', 'Library', 'xpc', 'launchd.plist')
    if not os.path.exists(path):
        print(f'ERROR: {path} not found!')
        return

    plist = load_plist(path)
    jobs = plist.get('LaunchDaemons', {})
    renamed = 0
    for job in jobs.values():
        if '_PanicOnCrash' in job:
            job['_PanicOnCrasX'] = job.pop('_PanicOnCrash')
            renamed += 1

    # Remove CommCenter baseband jobs that crash without modem hardware
    removed = [k for k, j in jobs.items() if j.get('Label') == 'com.apple.CommCenter']
    for k in removed:
        del jobs[k]

    save_plist(path, plist)
    print(f'  launchd.plist: {renamed} _PanicOnCrash renamed, {len(removed)} CommCenter jobs removed')


def setup_containers(root):
    """Create /private/var/containers/ subdirectories required by container manager."""
    print('Setting up container directories...')
    base = os.path.join(root, 'private', 'var', 'containers')
    for sub in ['Bundle', os.path.join('Data', 'System'), os.path.join('Shared', 'SystemGroup'), 'Temp']:
        d = os.path.join(base, sub)
        os.makedirs(d, exist_ok=True)
        print(f'  Created container: {d}')


def seed_mobileactivation(root):
    """Seed mobileactivationd data ark so iOS boots as Activated."""
    print('Seeding mobileactivationd data ark...')
    # Look for existing container or use standard UUID
    container_base = os.path.join(root, 'private', 'var', 'containers', 'Data', 'System')
    os.makedirs(container_base, exist_ok=True)
    
    # Standard container UUID used in SWEET v14
    target_uuid = 'D90C94C4-F94E-4FCF-8A28-A93BE3846D8E'
    internal_dir = os.path.join(container_base, target_uuid, 'Library', 'internal')
    os.makedirs(internal_dir, exist_ok=True)

    # Write metadata plist for the container
    meta_path = os.path.join(container_base, target_uuid, '.com.apple.mobile_container_manager.metadata.plist')
    save_plist(meta_path, {
        'MCMMetadataIdentifier': 'com.apple.mobileactivationd',
        'MCMMetadataCategory': 1,
        'MCMMetadataContainerClass': 13,
        'MCMMetadataInfo': {},
    })

    # Write data ark
    ark_path = os.path.join(internal_dir, 'data_ark.plist')
    save_plist(ark_path, {
        '-ActivationState': 'Activated',
        '-BrickState': False,
        '-BuildVersion': BUILD,
        '-ProductVersion': VERSION,
        '-DataMigrationCompleted': True,
        '-PreSydroDataMigrationCompleted': True,
    })
    print(f'  Seeded data ark: {ark_path}')


def patch_audio_and_media(root):
    """Disable VirtualAudio plugin and portrait recorder to prevent mediaserverd crash loop."""
    print('Applying audio and MediaToolbox workarounds...')
    src = os.path.join(root, 'Library', 'Audio', 'Plug-Ins', 'HAL', 'VirtualAudio.plugin')
    dst_dir = os.path.join(root, 'Library', 'Audio', 'Plug-Ins', 'HAL.disabled')
    if os.path.exists(src):
        os.makedirs(dst_dir, exist_ok=True)
        target = os.path.join(dst_dir, 'VirtualAudio.plugin')
        if os.path.exists(target):
            shutil.rmtree(target)
        shutil.move(src, dst_dir)
        print('  VirtualAudio.plugin moved to HAL.disabled')

    sub_configs = glob.glob(os.path.join(root, 'System', 'Library', 'Frameworks', 'MediaToolbox.framework', '*', 'SubServerConfiguration.plist'))
    for conf in sub_configs:
        try:
            data = load_plist(conf)
            data['StartRecorderServer'] = False
            save_plist(conf, data, fmt=plistlib.FMT_XML)
            print(f'  StartRecorderServer=False in {os.path.basename(os.path.dirname(conf))}')
        except Exception as e:
            print(f'  Warning: Could not update {conf}: {e}')


def setup_preferences(root):
    """Configure preferences to skip Setup.app and disable watchdogs."""
    print('Configuring SpringBoard and purplebuddy preferences...')
    merge_pref(root, 'com.apple.migration', {
        'LastSystemVersion': BUILD,
        'DMUserDataDisposition': {'SyntheticDidUpgrade': False, 'buildVersion': BUILD}
    })
    merge_pref(root, 'com.apple.springboard', {
        'BKNoWatchdogs': True,
        'FBLaunchWatchdogExceptions': {'com.apple.purplebuddy': 100.0},
        'MCForceShowCloudConfigurationUI': False
    })
    merge_pref(root, 'com.apple.purplebuddy', {
        'SetupDone': True,
        'SetupFinishedAllSteps': True,
        'SetupVersion': 11,
        'daemonizeNeedsToRun': False
    })
    merge_pref(root, 'com.apple.purplebuddy.notbackedup', {
        k: False for k in (
            'ShouldRunDiagnosticsMiniBuddy', 'ShouldRunHSA2MiniBuddy',
            'ShouldRunKeychainSyncMiniBuddy', 'ShouldRunMesaMiniBuddy',
            'ShouldRunPaymentMiniBuddy', 'ShouldRunStandardMiniBuddy',
            'SilentICDPUpgrade'
        )
    })
    merge_pref(root, 'com.apple.managedconfiguration.notbackedup', {
        'LockdownActivationIndicatesCloudConfigurationAvailable': False
    })


def main():
    if len(sys.argv) > 1:
        root = sys.argv[1]
    else:
        root = os.environ.get('IOS_ROOTFS', 'rootfs_build/os_root')

    print(f'=== SWEET RootFS Tweaks on {root} ===')
    if not os.path.isdir(os.path.join(root, 'System', 'Library', 'CoreServices')):
        print(f'Error: {root} does not look like an iOS rootfs!')
        sys.exit(1)

    setup_keybags_and_db(root)
    patch_launchd(root)
    setup_containers(root)
    seed_mobileactivation(root)
    patch_audio_and_media(root)
    setup_preferences(root)
    print('=== All tweaks successfully applied! ===')


if __name__ == '__main__':
    main()
