#!/bin/sh
# ==============================================================================
# Android Custom ROM (One UI 6 / S901E) Restore Script for Galaxy A05s
# Maintained by seif-zone <https://github.com/seif-zone/ios-samsung-a05s>
#
# Run this inside OrangeFox Recovery Terminal whenever you want to switch
# back to your Android system:
#   adb shell sh /external_sd/restore_android.sh
# ==============================================================================

set -e

echo ""
echo "=========================================================="
echo "    Android Restore Script for Samsung Galaxy A05s        "
echo "=========================================================="
echo ""

echo "[*] Step 1: Open OrangeFox Recovery GUI"
echo "    - Tap on 'Restore'"
echo "    - Select Storage: 'MicroSD Card'"
echo "    - Select your Android backup and swipe to Restore!"
echo ""
echo "[*] Step 2: Flash your Android boot image / Magisk if needed"
echo "    - Tap on 'Install'"
echo "    - Select your stock/custom boot.img -> Flash to 'Boot'"
echo ""
echo "[*] Step 3: Reboot to System -> Back to Android!"
echo ""
