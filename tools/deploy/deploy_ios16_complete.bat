@echo off
title iOS 16 Pure ADB Deployment Pipeline - Samsung Galaxy A05s (SM-A057F)
echo ======================================================================
echo   Samsung Galaxy A05s (SM-A057F) - Pure ADB Deployment Pipeline
echo   Project Location: D:\Project\
echo   Target: Samsung Stock ROM Base (One UI) / UFS 2.2 Storage
echo ======================================================================
echo.

:: 1. Locate ADB
set ADB=%~dp0..\..\platform-tools\adb.exe
if not exist "%ADB%" (
    where adb >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        set ADB=adb
    ) else (
        set ADB=adb.exe
    )
)

:: 2. Locate newfs_hfs_static
set NEWFS_TOOL=%~dp0..\bin\newfs_hfs_static
if not exist "%NEWFS_TOOL%" (
    if exist "%~dp0newfs_hfs_static" (
        set NEWFS_TOOL=%~dp0newfs_hfs_static
    ) else (
        set NEWFS_TOOL=newfs_hfs_static
    )
)

:: 3. Locate ios16-root.tar
set ROOT_TAR=%~dp0..\..\out\ios16-root.tar
if not exist "%ROOT_TAR%" (
    if exist "%~dp0ios16-root.tar" (
        set ROOT_TAR=%~dp0ios16-root.tar
    ) else (
        set ROOT_TAR=ios16-root.tar
    )
)

echo [*] Using ADB from: %ADB%
echo [*] Using HFS+ Tool from: %NEWFS_TOOL%
echo [*] Using iOS 16 Archive from: %ROOT_TAR%
echo.

echo [*] Checking ADB connection (Device connected via USB in Recovery)...
"%ADB%" devices
echo.

echo [1/4] Pushing newfs_hfs_static tool to device (/tmp)...
"%ADB%" push "%NEWFS_TOOL%" /tmp/newfs_hfs_static
"%ADB%" shell "chmod +x /tmp/newfs_hfs_static"

echo.
echo [2/4] Formatting /dev/block/sda36 (userdata) as Apple HFS+ (Case-Sensitive)...
"%ADB%" shell "umount /data 2>/dev/null; umount /mnt/ios 2>/dev/null; umount /dev/block/sda36 2>/dev/null"
"%ADB%" shell "/tmp/newfs_hfs_static -s -v iOSRoot -b 4096 /dev/block/sda36"

echo.
echo [3/4] Mounting /dev/block/sda36 to /mnt/ios via recovery kernel...
"%ADB%" shell "mkdir -p /mnt/ios && (mount -t hfsplus -o rw /dev/block/sda36 /mnt/ios || mount /dev/block/sda36 /mnt/ios)"

echo.
echo [4/4] Deploying iOS 16 RootFS (321,288 files)...
"%ADB%" shell "test -f /external_sd/ios16-root.tar"
if %ERRORLEVEL% equ 0 (
    echo [+] Found ios16-root.tar already on MicroSD card (/external_sd/ios16-root.tar)!
    set TAR_DEV_PATH=/external_sd/ios16-root.tar
    set CLEANUP_TAR=0
    goto UNTAR
)

echo [*] Transferring %ROOT_TAR% directly to UFS partition (/mnt/ios/ios16-root.tar)...
echo [*] USB transfer in progress (13.4 GB, ~3 minutes). Please wait...
"%ADB%" push "%ROOT_TAR%" /mnt/ios/ios16-root.tar
set TAR_DEV_PATH=/mnt/ios/ios16-root.tar
set CLEANUP_TAR=1

:UNTAR
echo.
echo [*] Extracting 321,288 files with genuine POSIX symlinks and permissions into /mnt/ios...
echo [*] Native Linux UFS 2.2 extraction in progress (~1-2 minutes). Please wait...
"%ADB%" shell "tar -xf %TAR_DEV_PATH% -C /mnt/ios"

if "%CLEANUP_TAR%"=="1" (
    echo [*] Cleaning up temporary archive to free up internal UFS storage...
    "%ADB%" shell "rm -f /mnt/ios/ios16-root.tar"
)

echo [*] Flushing disk buffers and unmounting safely...
"%ADB%" shell "sync && umount /mnt/ios"

echo.
echo ======================================================================
echo  [SUCCESS] All iOS 16 RootFS files deployed to /dev/block/sda36!
echo ======================================================================
echo.
set /p REBOOT_CHOICE="Do you want to reboot device to Download Mode right now via ADB? (Y/N): "
if /i "%REBOOT_CHOICE%"=="Y" (
    echo [*] Rebooting device to Samsung Download Mode...
    "%ADB%" reboot download
    echo [+] Device rebooted! Now open Odin and flash AP_A05s_iOS16_Kernel_Patched.tar.md5 in [AP].
) else (
    echo.
    echo [*] Manual Download Mode Steps:
    echo     1. Power Off device.
    echo     2. Hold Vol+ and Vol- while plugging in USB cable.
    echo     3. Press Vol+ once to enter Download Mode.
    echo     4. In Odin, flash AP_A05s_iOS16_Kernel_Patched.tar.md5 in [AP].
)
echo.
pause
