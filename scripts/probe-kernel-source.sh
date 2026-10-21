#!/usr/bin/env bash
# Index a Kirin vendor kernel tree for a UEFI port.
# Usage: probe-kernel-source.sh <kernel-source-dir> [outdir]
set -uo pipefail

SRC="${1:?usage: probe-kernel-source.sh <kernel-source-dir> [outdir]}"
OUT="${2:-kernel-probe}"
mkdir -p "$OUT"

KVERSION="unknown"
eval "$(awk -F' = ' '
  /^VERSION =/     {v=$2}
  /^PATCHLEVEL =/  {p=$2}
  /^SUBLEVEL =/    {s=$2}
  END {printf "KVERSION=%s.%s.%s\n", v, p, s}
' "$SRC/Makefile" 2>/dev/null)"

{
  echo "source     : $SRC"
  echo "kernel     : $KVERSION"
  echo "generated  : $(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$OUT/summary.txt"

DTS="$SRC/arch/arm64/boot/dts"

if [ -d "$DTS" ]; then
  find "$DTS" -type f \( -name '*.dts' -o -name '*.dtsi' \) | sort > "$OUT/dts-files.txt" || true
  ls "$DTS/hisilicon" > "$OUT/hisilicon-dts.txt" 2>/dev/null || true
  grep -RIn --include='*.dts*' -E 'hi3690|kirin.?990|hisilicon,.*990' "$DTS" \
    > "$OUT/kirin-dts.txt" 2>/dev/null || true
fi

if [ ! -s "$OUT/kirin-dts.txt" ]; then
  cat >> "$OUT/summary.txt" <<'EOF'
kirin dts : MISSING

This tree has no board device tree for Kirin 990. The board memory map,
UART/UFS/PMIC/GPIO/ramoops addresses must come from the device's own
dtb/dtbo partitions. Use scripts/dump-dtb.sh.
EOF
fi

find "$SRC/arch/arm64/configs" -maxdepth 1 -type f 2>/dev/null \
  | sed 's#.*/##' | sort > "$OUT/defconfigs.txt" || true

find "$SRC/platform_source" -maxdepth 2 -type d 2>/dev/null \
  | sort > "$OUT/platform-source-dirs.txt" || true

find "$SRC/drivers" "$SRC/platform_source" -type f \
  \( -iname '*ufs*' -o -iname '*pmic*' -o -iname '*gpio*' -o -iname '*dsi*' \) \
  2>/dev/null | head -500 > "$OUT/related-files.txt" || true

grep -RIn --include='*.h' \
  -E '#define[[:space:]]+[A-Z0-9_]*(UFS|UART|PMIC|GPIO|DSI|MBOX)[A-Z0-9_]*_(BASE|PHYS|ADDR)' \
  "$SRC/drivers" "$SRC/platform_source" 2>/dev/null \
  | head -300 > "$OUT/register-bases.txt" || true

grep -RIn --include='*.dts*' -E 'ramoops|pstore' "$DTS" \
  > "$OUT/ramoops.txt" 2>/dev/null || true

{
  echo
  echo "kernel version   : $KVERSION"
  echo "dts files        : $(wc -l < "$OUT/dts-files.txt" 2>/dev/null || echo 0)"
  echo "kirin dts hits   : $(wc -l < "$OUT/kirin-dts.txt" 2>/dev/null || echo 0)"
  echo "defconfigs       : $(wc -l < "$OUT/defconfigs.txt" 2>/dev/null || echo 0)"
  echo "related drivers  : $(wc -l < "$OUT/related-files.txt" 2>/dev/null || echo 0)"
  echo "register defines : $(wc -l < "$OUT/register-bases.txt" 2>/dev/null || echo 0)"
} >> "$OUT/summary.txt"

cat "$OUT/summary.txt"
