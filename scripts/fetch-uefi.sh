#!/usr/bin/env bash
# Fetch (or refresh) Mu-Silicium at a pinned ref.
#
# Mu-Silicium's submodule tree includes giant optional test dependencies
# (OpenSSL's BoringSSL/quiche/fuzz corpora, libspdm, ...). The EDK2 build
# only needs the top-level modules listed below, so do NOT recurse.
set -euo pipefail

DEST="${1:-Mu-Silicium}"
REF="${2:-main}"
REPO="${MU_REPO:-https://github.com/Project-Silicium/Mu-Silicium.git}"

export GIT_HTTP_VERSION=HTTP/1.1
git config --global http.postBuffer 524288000 || true
git config --global http.lowSpeedLimit 1000 || true
git config --global http.lowSpeedTime 300 || true

SUBMODULES=(
  Binaries
  Common/Mu
  Common/Mu_OEM_Sample
  Mu_Basecore
  Silicium-ACPI
  Silicon/Silicium/OpensslPkg/Library/OpensslLib/openssl
)

clone_once() {
  rm -rf "$DEST"
  git clone --depth 1 --single-branch --branch "$REF" "$REPO" "$DEST"
}

init_submodules() {
  git -C "$DEST" submodule sync
  git -C "$DEST" submodule update --init --depth 1 "${SUBMODULES[@]}"

  # libfdt is used by BaseFdtLib/DtPlatformDxe; its nested module is small.
  git -C "$DEST/Mu_Basecore" submodule update --init --depth 1 \
    MdePkg/Library/BaseFdtLib/libfdt || true
}

if [ -d "$DEST/.git" ]; then
  echo "==> refresh $DEST @ $REF"
  git -C "$DEST" fetch --depth 1 origin "$REF"
  git -C "$DEST" checkout -f FETCH_HEAD
  init_submodules
else
  for attempt in 1 2 3; do
    echo "==> clone attempt $attempt"
    if clone_once && init_submodules; then
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
