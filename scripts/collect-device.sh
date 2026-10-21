#!/usr/bin/env bash
# Collect everything needed before writing a Kirin platform package.
# Run in adb mode (booted Android) and again in fastboot mode.
set -uo pipefail

OUT="${1:-device-report-$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$OUT"

say() { printf '==> %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

if have fastboot && fastboot devices 2>/dev/null | grep -q .; then
  say "fastboot device detected"
  fastboot getvar all > "$OUT/fastboot-getvar.txt" 2>&1 || true
  fastboot oem get-bootinfo > "$OUT/fastboot-bootinfo.txt" 2>&1 || true
  fastboot oem lock-state info > "$OUT/fastboot-lockstate.txt" 2>&1 || true
  fastboot oem get-product-model > "$OUT/fastboot-product.txt" 2>&1 || true
  fastboot oem get-build-number > "$OUT/fastboot-build.txt" 2>&1 || true
  fastboot getvar unlocked > "$OUT/fastboot-unlocked.txt" 2>&1 || true
fi

if have adb && adb devices 2>/dev/null | awk 'NR>1 && $2=="device"{found=1} END{exit !found}'; then
  say "adb device detected"
  adb shell getprop > "$OUT/props.txt" 2>&1 || true
  adb shell cat /proc/cmdline > "$OUT/cmdline.txt" 2>&1 || true
  adb shell cat /proc/partitions > "$OUT/partitions.txt" 2>&1 || true
  adb shell ls -l /dev/block/by-name > "$OUT/by-name.txt" 2>&1 || true
  adb shell ls -l /dev/block/bootdevice/by-name > "$OUT/bootdevice-by-name.txt" 2>&1 || true
  adb shell cat /proc/iomem > "$OUT/iomem.txt" 2>&1 || true
  adb shell cat /proc/meminfo > "$OUT/meminfo.txt" 2>&1 || true
  adb shell dmesg > "$OUT/dmesg.txt" 2>&1 || true
  adb shell ls -l /sys/fs/pstore > "$OUT/pstore.txt" 2>&1 || true
  adb shell getprop ro.boot.bootloader > "$OUT/bootloader.txt" 2>&1 || true
  adb shell getprop ro.boot.slot_suffix > "$OUT/slot.txt" 2>&1 || true

  say "trying to dump the boot partition (needs root)"
  if adb shell 'su -c "dd if=/dev/block/by-name/boot of=/data/local/tmp/stock_boot.img"' >/dev/null 2>&1; then
    adb pull /data/local/tmp/stock_boot.img "$OUT/stock_boot.img" >/dev/null 2>&1 || true
    adb shell rm -f /data/local/tmp/stock_boot.img >/dev/null 2>&1 || true
  fi

  say "dumping device tree"
  bash "$(dirname "$0")/dump-dtb.sh" "$OUT/dtb" >/dev/null 2>&1 || true
fi

say "report written to $OUT"
ls -l "$OUT"
