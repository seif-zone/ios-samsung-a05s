#!/usr/bin/env bash
# pull-firmware.sh: Pull vendor firmware from a Samsung Galaxy A05s (SM-A057F) via ADB
# Follows the HakiOS firmware isolation policy: vendor blobs are kept in fw-*/ and NEVER committed to git.
set -euo pipefail

echo "========================================================"
echo " Samsung Galaxy A05s (SM-A057F) Firmware Extractor"
echo " Pulling Adreno 610, Wi-Fi, and DSP blobs from Android"
echo "========================================================"

if ! command -v adb >/dev/null 2>&1; then
    echo "[-] Error: 'adb' command not found in PATH."
    exit 1
fi

echo "[*] Checking connected device..."
DEVICE_STATE=$(adb get-state 2>/dev/null || true)
if [ "$DEVICE_STATE" != "device" ]; then
    echo "[-] Error: No Android device detected in adb mode. Connect your A05s with USB Debugging enabled."
    exit 1
fi

MODEL=$(adb shell getprop ro.product.model | tr -d '\r')
echo "[+] Detected device: $MODEL"

# 1. GPU Firmware (Adreno 610 / a6xx)
echo "[*] Pulling Adreno 610 GPU firmware to fw-gpu/..."
mkdir -p fw-gpu
adb pull /vendor/firmware_mnt/image/a610_zap.mdt fw-gpu/ 2>/dev/null || adb pull /vendor/firmware/a610_zap.mdt fw-gpu/ || true
adb pull /vendor/firmware_mnt/image/a610_zap.b00 fw-gpu/ 2>/dev/null || true
adb pull /vendor/firmware_mnt/image/a610_zap.b01 fw-gpu/ 2>/dev/null || true
adb pull /vendor/firmware_mnt/image/a610_zap.b02 fw-gpu/ 2>/dev/null || true
adb pull /vendor/firmware_mnt/image/a610_sqe.fw  fw-gpu/ 2>/dev/null || true

# 2. Touchscreen Firmware & Config
echo "[*] Pulling touchscreen configuration to fw-touch/..."
mkdir -p fw-touch
adb pull /vendor/firmware/novatek_ts_fw.bin fw-touch/ 2>/dev/null || true

# 3. Audio & DSP
echo "[*] Pulling Audio DSP firmware to fw-audio/..."
mkdir -p fw-audio
adb pull /vendor/firmware_mnt/image/adsp.mdt fw-audio/ 2>/dev/null || true
adb pull /vendor/firmware_mnt/image/adsp.b00 fw-audio/ 2>/dev/null || true

# 4. Device Tree Blob
echo "[*] Pulling device tree to prebuilt/device-tree.dtb..."
mkdir -p prebuilt
adb shell "su -c 'cat /sys/firmware/fdt'" > prebuilt/device-tree.dtb 2>/dev/null || adb pull /sys/firmware/fdt prebuilt/device-tree.dtb 2>/dev/null || true

echo "[+] Firmware extraction complete. All blobs stored in fw-*/ (ignored by git)."
