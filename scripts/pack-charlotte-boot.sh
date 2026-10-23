#!/usr/bin/env bash
# Replace the kernel in the stock MRO-W00 boot.img with the custom Image.gz,
# preserving the stock ramdisk / DTB / AVB tail (charlotte-mainline style).
#
# Usage:
#   ./scripts/pack-charlotte-boot.sh <stock-boot.img> <Image.gz> [out.img]
#
# The resulting image is still subject to the TEE UEFI's DecryptKernel/HVB;
# unlock/decrypt the secboot first (README_Version.txt).
set -euo pipefail

STOCK=${1:?usage: $0 <stock-boot.img> <Image.gz> [out.img]}
IMAGE=${2:?}
OUT=${3:-boot-charlotte.img}
ROOT=$(cd "$(dirname "$0")/.." && pwd)

test -f "$STOCK" || { echo "missing stock boot.img: $STOCK" >&2; exit 1; }
test -f "$IMAGE" || { echo "missing Image.gz: $IMAGE" >&2; exit 1; }

python3 "$ROOT/scripts/repack-bootimg.py" \
  --stock "$STOCK" \
  --kernel "$IMAGE" \
  --out "$OUT" \
  --keep-tail

ls -lh "$OUT"
