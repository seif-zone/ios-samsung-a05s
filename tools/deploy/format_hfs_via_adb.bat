@echo off
title iOS 16 HFS+ RootFS Setup over ADB - Samsung A05s
echo ==========================================================
echo   Samsung Galaxy A05s (SM-A057F) - iOS 16 RootFS Setup
echo ==========================================================
echo.

set ADB=adb

echo [*] Checking ADB connection...
"%ADB%" devices
echo.

echo [*] Pushing newfs_hfs and hfs_static tools to device /tmp...
"%ADB%" push "%~dp0..\bin\newfs_hfs_static" /tmp/newfs_hfs_static
"%ADB%" push "%~dp0..\bin\hfs_static" /tmp/hfs_static
"%ADB%" shell "chmod +x /tmp/newfs_hfs_static /tmp/hfs_static"

echo [*] Unmounting /data and /dev/block/sda36...
"%ADB%" shell "umount /data 2>/dev/null; umount /dev/block/sda36 2>/dev/null"

echo [*] Formatting /dev/block/sda36 (userdata) as Case-Sensitive Apple HFS+...
"%ADB%" shell "/tmp/newfs_hfs_static -s -v iOSRoot -b 4096 /dev/block/sda36"

echo.
echo ==========================================================
echo  [SUCCESS] Partition /dev/block/sda36 formatted as HFS+!
echo  Ready for iOS 16 RootFS and Kernel Boot!
echo ==========================================================
echo.
pause
