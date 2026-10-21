#!/usr/bin/env bash
# Dump the board device tree from a rooted Huawei device.
# Usage: dump-dtb.sh [outdir] [adb-serial]
set -uo pipefail

OUT="${1:-dtb-report}"
SERIAL="${2:-}"
ADB=(adb)
if [ -n "$SERIAL" ]; then
  ADB=(adb -s "$SERIAL")
fi

mkdir -p "$OUT"

have() { command -v "$1" >/dev/null 2>&1; }

dump_part() {
  local name="$1"
  if "${ADB[@]}" shell "su -c 'ls /dev/block/by-name/$name'" >/dev/null 2>&1; then
    "${ADB[@]}" shell "su -c 'dd if=/dev/block/by-name/$name of=/data/local/tmp/$name.img'" >/dev/null 2>&1 || return
    "${ADB[@]}" pull "/data/local/tmp/$name.img" "$OUT/$name.img" >/dev/null 2>&1 || return
    "${ADB[@]}" shell "rm -f /data/local/tmp/$name.img" >/dev/null 2>&1 || true
    echo "==> dumped $name"
  else
    echo "==> $name partition not found" >&2
  fi
}

dump_part dtb
dump_part dtbo

echo "==> copying live /proc/device-tree as fallback"
"${ADB[@]}" shell "su -c 'rm -rf /data/local/tmp/dt && cp -r /proc/device-tree /data/local/tmp/dt'" >/dev/null 2>&1 \
  && "${ADB[@]}" pull /data/local/tmp/dt "$OUT/device-tree" >/dev/null 2>&1 \
  && echo "==> copied /proc/device-tree" \
  || echo "==> /proc/device-tree copy failed (needs root)" >&2
"${ADB[@]}" shell "rm -rf /data/local/tmp/dt" >/dev/null 2>&1 || true

if have dtc; then
  for img in "$OUT"/*.img; do
    [ -f "$img" ] || continue
    if dtc -I dtb -O dts -o "${img%.img}.dts" "$img" 2>"$OUT/$(basename "$img").dtc.log"; then
      echo "==> decompiled $(basename "$img")"
    else
      echo "==> dtc could not parse $(basename "$img") (raw dtbo table?)" >&2
    fi
  done
else
  echo "==> dtc not installed, skipping decompile" >&2
fi

if [ -f "$OUT/dtbo.img" ] && have mkdtimg; then
  mkdir -p "$OUT/dtbo"
  mkdtimg dump "$OUT/dtbo.img" -b "$OUT/dtbo" >/dev/null 2>&1 || true
  if have dtc; then
    for blob in "$OUT"/dtbo/*; do
      [ -f "$blob" ] || continue
      dtc -I dtb -O dts -o "$blob.dts" "$blob" 2>/dev/null || true
    done
  fi
  echo "==> split dtbo entries"
fi

if [ -d "$OUT/device-tree" ] && have dtc; then
  if dtc -I fs -O dts -o "$OUT/runtime.dts" "$OUT/device-tree" 2>"$OUT/runtime.dtc.log"; then
    echo "==> wrote runtime.dts (from live /proc/device-tree)"
  else
    echo "==> dtc -I fs failed, see runtime.dtc.log" >&2
  fi
fi

if [ -d "$OUT/device-tree" ]; then
  while IFS= read -r reg; do
    echo "--- $reg"
    od -An -tx1 "$reg"
  done < <(find "$OUT/device-tree" -name reg -type f 2>/dev/null) \
    > "$OUT/device-tree-regs.txt" 2>/dev/null || true
fi

echo "==> report in $OUT"
ls -l "$OUT"
