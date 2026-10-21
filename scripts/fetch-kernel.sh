#!/usr/bin/env bash
# Fetch (or refresh) the Kirin 990 vendor kernel at a pinned ref.
set -uo pipefail

DEST="${1:-Mu-Kernel}"
REF="${2:-2f71c5e433024c76412bab655e6ff54b3e656ca8}"
REPO="${KERNEL_REPO:-https://github.com/HK416AAA/android_kernel_LIO_kirin990_103.git}"

if [ ! -d "$DEST/.git" ]; then
  mkdir -p "$DEST"
  git -C "$DEST" init -q
  git -C "$DEST" remote add origin "$REPO"
fi

echo "==> fetching $REF"
if ! git -C "$DEST" fetch --depth 1 origin "$REF"; then
  echo "==> ref $REF not fetchable, falling back to main" >&2
  git -C "$DEST" fetch --depth 1 origin main
fi

git -C "$DEST" checkout -f FETCH_HEAD
git -C "$DEST" rev-parse HEAD | tee "$DEST/.ci-revision"
