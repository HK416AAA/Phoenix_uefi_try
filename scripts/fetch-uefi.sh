#!/usr/bin/env bash
# Fetch (or refresh) Mu-Silicium at a pinned ref, including submodules.
# Mu-Silicium is ~5 GB, so this is deliberately defensive: HTTP/1.1,
# parallel shallow submodules, and retries with a clean restart.
set -euo pipefail

DEST="${1:-Mu-Silicium}"
REF="${2:-main}"
REPO="${MU_REPO:-https://github.com/Project-Silicium/Mu-Silicium.git}"

export GIT_HTTP_VERSION=HTTP/1.1
git config --global http.postBuffer 524288000 || true
git config --global http.lowSpeedLimit 1000 || true
git config --global http.lowSpeedTime 300 || true

clone_once() {
  rm -rf "$DEST"
  git clone --depth 1 --single-branch --branch "$REF" \
    --recurse-submodules --shallow-submodules --jobs 4 \
    "$REPO" "$DEST"
}

if [ -d "$DEST/.git" ]; then
  echo "==> refresh $DEST @ $REF"
  git -C "$DEST" fetch --depth 1 origin "$REF"
  git -C "$DEST" checkout -f FETCH_HEAD
  git -C "$DEST" submodule sync --recursive
  git -C "$DEST" submodule update --init --recursive --depth 1 --jobs 4
else
  for attempt in 1 2 3; do
    echo "==> clone attempt $attempt"
    if clone_once; then
      break
    fi
    echo "==> clone failed, retrying in 15s" >&2
    sleep 15
  done
  if [ ! -d "$DEST/.git" ]; then
    echo "==> clone failed after 3 attempts" >&2
    exit 1
  fi
fi

git -C "$DEST" rev-parse HEAD > "$DEST/.ci-revision"
echo "==> revision $(cat "$DEST/.ci-revision")"
