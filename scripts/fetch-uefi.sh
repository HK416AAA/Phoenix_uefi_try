#!/usr/bin/env bash
# Fetch (or refresh) Mu-Silicium at a pinned ref, including submodules.
set -euo pipefail

DEST="${1:-Mu-Silicium}"
REF="${2:-main}"
REPO="${MU_REPO:-https://github.com/Project-Silicium/Mu-Silicium.git}"

if [ -d "$DEST/.git" ]; then
  echo "==> refresh $DEST @ $REF"
  git -C "$DEST" fetch --depth 1 origin "$REF"
  git -C "$DEST" checkout -f FETCH_HEAD
  git -C "$DEST" submodule sync --recursive
  git -C "$DEST" submodule update --init --recursive --depth 1
else
  echo "==> clone $REPO @ $REF into $DEST"
  git clone --depth 1 --branch "$REF" \
    --recurse-submodules --shallow-submodules \
    "$REPO" "$DEST"
fi

git -C "$DEST" rev-parse HEAD > "$DEST/.ci-revision"
echo "==> revision $(cat "$DEST/.ci-revision")"
