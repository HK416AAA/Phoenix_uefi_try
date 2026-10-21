#!/usr/bin/env python3
"""Validate the gzip payload produced by the build-stub workflow."""
from __future__ import annotations

import gzip
import struct
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: verify-stub.py <stub.bin.gz>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    stored = path.read_bytes()
    image = gzip.decompress(stored) if stored[:2] == b"\x1f\x8b" else stored

    print(f"file        : {path}")
    print(f"stored      : {len(stored)} bytes")
    print(f"decompressed: {len(image)} bytes")

    if len(image) < 0x40:
        print("FAIL: payload smaller than the 64-byte Image header")
        return 1

    text_offset, image_size, flags = struct.unpack_from("<QQQ", image, 8)
    magic = image[0x38:0x3C]
    print(f"magic       : {magic!r}")
    print(f"text_offset : {text_offset:#x}")
    print(f"image_size  : {image_size:#x}")
    print(f"flags       : {flags:#x}")

    if magic != b"ARM\x64":
        print("FAIL: ARM64 Image magic missing at 0x38")
        return 1
    if image_size != len(image):
        print(f"WARN: image_size {image_size:#x} != payload {len(image):#x}")
    print("OK: payload looks like a bootable ARM64 Image")
    return 0


if __name__ == "__main__":
    sys.exit(main())
