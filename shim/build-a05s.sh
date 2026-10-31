#!/bin/bash
# Build the shim and wrap it in a boot.img v2 for Samsung Galaxy A05s (SM-A057F / m269).
# Samsung ABL expects boot image header version 2 (BOARD_BOOTIMG_HEADER_VERSION := 2).
set -euo pipefail
cd "$(dirname "$0")"

CC=${CROSS_COMPILE:-aarch64-linux-gnu-}gcc
OBJCOPY=${CROSS_COMPILE:-aarch64-linux-gnu-}objcopy
CFLAGS="-O2 -ffreestanding -nostdlib -fno-pic -mgeneral-regs-only -mstrict-align -fno-stack-protector -Wall -Wextra"

mkdir -p out

echo "[*] Compiling A05s shim objects..."
for f in start.S shim.c console.c mmu.c fdt.c loader.c ufs.c; do
	$CC $CFLAGS -c $f -o out/${f%.*}.o
done

# The image runs wherever ABL puts it with no relocation pass: only the
# header's image_size (start.o, linked at 0) may be an absolute address.
abs=$(${CROSS_COMPILE:-aarch64-linux-gnu-}readelf -r out/shim.o out/console.o out/mmu.o out/fdt.o out/loader.o out/ufs.o | grep -c ABS64 || true)
[ "$abs" = 0 ] || { echo "error: $abs absolute relocations in C objects" >&2; exit 1; }

echo "[*] Linking shim.elf..."
$CC $CFLAGS -static -T shim.ld -Wl,--build-id=none -Wl,--no-warn-rwx-segments -Wl,-N \
	out/start.o out/shim.o out/console.o out/mmu.o out/fdt.o out/loader.o out/ufs.o -o out/shim.elf
$OBJCOPY -O binary out/shim.elf out/Image

# ABL copies the file; pad to image_size so .bss/stacks exist as zeroed bytes.
size=$((16#$(${CROSS_COMPILE:-aarch64-linux-gnu-}nm out/shim.elf | awk '$3=="_end"{print $1}')))
truncate -s "$size" out/Image

# Ramdisk: an xnu payload (tools/mkpayload.py) if given as $1, else an empty newc cpio.
if [ -n "${1:-}" ]; then
	echo "[*] Appending XNU payload ($1) to Image at 4K boundary..."
	truncate -s $(( (size + 0xfff) & ~0xfff )) out/Image
	cat "$1" >> out/Image
	python3 -c 'import os,struct,sys; f=open(sys.argv[1],"r+b"); f.seek(16); f.write(struct.pack("<Q", os.path.getsize(sys.argv[1])))' out/Image
fi

(cd out && rm -rf rd && mkdir rd && cd rd && find . | cpio -o -H newc --quiet | gzip -9 > ../ramdisk.bin)

MKBOOTIMG=${MKBOOTIMG:-mkbootimg}
echo "[*] Packing Samsung A05s boot.img (Header Version 2)..."
$MKBOOTIMG \
	--header_version 2 \
	--kernel out/Image \
	--ramdisk out/ramdisk.bin \
	--base 0x00000000 \
	--pagesize 4096 \
	--os_version 13.0.0 \
	--os_patch_level 2025-01 \
	--cmdline "console=null earlycon=msm_geni_serial,0x4a90000 sweetfb_console=1" \
	-o out/a05s-boot.img

echo "[+] Successfully created out/a05s-boot.img"
ls -lh out/Image out/a05s-boot.img
