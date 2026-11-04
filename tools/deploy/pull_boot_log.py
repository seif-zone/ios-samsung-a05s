#!/usr/bin/env python3
"""Pull Darwin XNU persistent console log ring buffer (4 MiB) from UFS storage on Samsung Galaxy A05s.
Usage:
    python3 tools/deploy/pull_boot_log.py [OUTPUT_FILE]
"""
import subprocess, sys, os, struct

def run_adb(cmd):
    p = subprocess.run(['adb'] + cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return p.stdout.strip()

def main():
    out_file = sys.argv[1] if len(sys.argv) > 1 else 'boot_panic_log.txt'
    dev = "/dev/block/sda36"
    print(f"[+] Target partition: {dev}")

    # Verify device presence
    devices = run_adb(['devices'])
    if 'recovery' not in devices and 'device' not in devices:
        print("[-] Error: No ADB device detected. Please boot phone into OrangeFox Recovery.")
        sys.exit(1)

    size_str = run_adb(['shell', f'blockdev --getsize64 {dev}'])
    if not size_str.isdigit():
        print(f"[-] Error: Failed to get size of {dev}: {size_str}")
        sys.exit(1)

    total_bytes = int(size_str)
    block_size = 4096
    count = 1025
    skip = (total_bytes // block_size) - count
    print(f"[+] Total blocks: {total_bytes // block_size:,}, reading {count} blocks at offset {skip}...")

    # Read binary blocks via adb exec-out
    p = subprocess.run(['adb', 'exec-out', f'dd if={dev} bs={block_size} skip={skip} count={count} 2>/dev/null'],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    data = p.stdout
    print(f"[+] Retrieved {len(data):,} bytes")

    if len(data) < 4096:
        print("[-] Error: Incomplete read from partition.")
        sys.exit(1)

    magic = data[:8]
    if magic == b'SWEETLOG':
        magic, version, size, total, seq = struct.unpack_from('<8sIIQQ', data, 0)
        print(f"[+] Header: version={version}, ring_size={size:,}, total_logged={total:,}, seq={seq}")
        ring = data[4096:4096 + size]
        if total <= size:
            text_bytes = ring[:total]
        else:
            start = total % size
            text_bytes = ring[start:] + ring[:start]
        decoded = text_bytes.decode('utf-8', errors='replace').replace('\r', '')
    else:
        # Search for magic anywhere in buffer or extract printable text
        idx = data.find(b'SWEETLOG')
        if idx != -1:
            print(f"[+] Found SWEETLOG at offset {idx}")
            magic, version, size, total, seq = struct.unpack_from('<8sIIQQ', data, idx)
            ring = data[idx + 4096:idx + 4096 + size]
            decoded = ring[:min(total, len(ring))].decode('utf-8', errors='replace').replace('\r', '')
        else:
            printable = bytes([c for c in data[4096:] if 32 <= c <= 126 or c in (10, 13)])
            decoded = printable.decode('utf-8', errors='replace')

    with open(out_file, 'w', encoding='utf-8', errors='replace') as out:
        out.write(decoded)

    print(f"[SUCCESS] Wrote {len(decoded):,} log characters to {out_file}")

if __name__ == '__main__':
    main()
