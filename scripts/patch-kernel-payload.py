#!/usr/bin/env python3
"""Append a payload to an ARM64 Linux Image and redirect its entry branch.

HHEE accepts the stock kernel image but appears to refuse a bare stub.
This tool keeps the stock kernel as a carrier: code0 is replaced with a
branch to a payload appended at the end of the image, and image_size is
kept large enough for HHEE's mapping.

    python patch-kernel-payload.py --kernel stock-kernel.gz \
        --payload builds/stub-reset.bin --out carrier-reset.gz
"""
from __future__ import annotations

import argparse
import gzip
import struct
import sys
from pathlib import Path

ALIGN = 0x1000


def align_up(value: int, alignment: int) -> int:
    return (value + alignment - 1) // alignment * alignment


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kernel", required=True, help="stock Image or Image.gz")
    parser.add_argument("--payload", required=True, help="raw payload appended at the end")
    parser.add_argument("--out", required=True, help="output Image.gz")
    parser.add_argument("--after-image-size", action="store_true",
                        help="place the payload after image_size (outside the original BSS)")
    args = parser.parse_args()

    raw = Path(args.kernel).read_bytes()
    image = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
    if len(image) < 64 or image[56:60] != b"ARM\x64":
        print("FAIL: not an ARM64 Image", file=sys.stderr)
        return 1

    text_offset, old_size, flags = struct.unpack_from("<QQQ", image, 8)
    payload = Path(args.payload).read_bytes()
    if payload[:2] == b"\x1f\x8b":
        payload = gzip.decompress(payload)

    offset = align_up(old_size if args.after_image_size else len(image), ALIGN)
    out_image = bytearray(image)
    out_image += b"\0" * (offset - len(out_image))
    out_image += payload

    # ARM64 b: 0x14000000 | imm26, imm26 = (target - pc) / 4.
    imm26 = (offset >> 2) & 0x03FFFFFF
    struct.pack_into("<I", out_image, 0, 0x14000000 | imm26)
    if args.after_image_size:
        new_size = offset + len(payload)
    else:
        new_size = max(old_size, len(out_image))
    struct.pack_into("<Q", out_image, 16, new_size)

    compressed = gzip.compress(bytes(out_image), compresslevel=9)
    Path(args.out).write_bytes(compressed)

    target = offset
    print(f"kernel image : {len(image):#x}")
    print(f"payload      : {len(payload):#x} at {offset:#x}")
    print(f"branch       : code0 -> {target:#x} (imm26 {imm26:#x})")
    print(f"image_size   : old {old_size:#x} -> new {new_size:#x}")
    print(f"gzip         : {len(compressed):#x}")
    print(f"wrote        : {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
