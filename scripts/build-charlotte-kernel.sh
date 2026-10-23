#!/usr/bin/env bash
# Build a charlotte (Kirin 9010 / MRO-W00) kernel Image.gz from the official
# Huawei open-source kernel tree, using the stock config as the defconfig.
#
# Usage:
#   ./scripts/build-charlotte-kernel.sh /path/to/Code_Opensource/kernel [out-dir]
#
# Toolchain (from the official README_Kernel.txt):
#   export CROSS_COMPILE=aarch64-linux-android-
#   clang-r353983c on PATH or kernel/../../prebuilts/clang/host/linux-x86
set -euo pipefail

SRC=${1:?usage: $0 <kernel-source> [out-dir]}
OUT=${2:-$(pwd)/out-charlotte}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
DEF="$ROOT/platforms/Huawei/charlottePkg/Resources/merge_charlotte_defconfig"

test -d "$SRC/arch/arm64" || {
  echo "not a kernel tree: $SRC" >&2
  exit 1
}

cp "$DEF" "$SRC/arch/arm64/configs/merge_charlotte_defconfig"

export ARCH=arm64
export CROSS_COMPILE=${CROSS_COMPILE:-aarch64-linux-android-}

mkdir -p "$OUT"
make -C "$SRC" O="$OUT" merge_charlotte_defconfig
make -C "$SRC" O="$OUT" -j"$(nproc)"

ls -lh "$OUT/arch/arm64/boot/Image.gz"
echo "pack with: ./scripts/pack-charlotte-boot.sh <stock-boot.img> $OUT/arch/arm64/boot/Image.gz"
