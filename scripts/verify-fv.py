#!/usr/bin/env python3
"""Structural check for an EDK2 firmware volume (SILICIUM_UEFI.fd).

This only proves the FV header/block map are self-consistent. It says nothing
about whether the firmware can run on real hardware.
"""
import argparse
import struct
import sys
from pathlib import Path

FV_SIGNATURE = b"_FVH"


def u16(buf: bytes, off: int) -> int:
    return struct.unpack_from("<H", buf, off)[0]


def u32(buf: bytes, off: int) -> int:
    return struct.unpack_from("<I", buf, off)[0]


def u64(buf: bytes, off: int) -> int:
    return struct.unpack_from("<Q", buf, off)[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fd", help="path to SILICIUM_UEFI.fd")
    parser.add_argument("--min-size", type=int, default=64 * 1024)
    args = parser.parse_args()

    path = Path(args.fd)
    if not path.is_file():
        print(f"FAIL: {path} does not exist")
        return 2

    data = path.read_bytes()
    errors: list[str] = []

    if len(data) < 64:
        errors.append(f"file is too small: {len(data)} bytes")
        print("\n".join(f"FAIL: {e}" for e in errors))
        return 1

    fv_length = u64(data, 32)
    signature = data[40:44]
    header_length = u16(data, 48)

    if signature != FV_SIGNATURE:
        errors.append(f"bad FV signature at 0x28: {signature!r}")
    if fv_length == 0 or fv_length > len(data):
        errors.append(f"FvLength {fv_length:#x} exceeds file size {len(data):#x}")
    if header_length < 56 or header_length > len(data):
        errors.append(f"HeaderLength {header_length:#x} is invalid")

    block_total = 0
    off = 56
    while off + 8 <= len(data):
        num_blocks = u32(data, off)
        block_length = u32(data, off + 4)
        off += 8
        if num_blocks == 0 and block_length == 0:
            break
        block_total += num_blocks * block_length

    if block_total and fv_length and block_total != fv_length:
        errors.append(f"block map total {block_total:#x} != FvLength {fv_length:#x}")
    if len(data) < args.min_size:
        errors.append(f"image is smaller than --min-size {args.min_size:#x}")

    print(f"file       : {path}")
    print(f"size       : {len(data):#x} ({len(data)} bytes)")
    print(f"FvLength   : {fv_length:#x}")
    print(f"HeaderLen  : {header_length:#x}")
    print(f"block map  : {block_total:#x}")

    if errors:
        print()
        for error in errors:
            print(f"FAIL: {error}")
        return 1

    print("OK: firmware volume header is self-consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
