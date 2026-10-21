#!/usr/bin/env python3
"""Build a throwaway boot image that just loops forever.

Purpose: check whether the device's ABL accepts an unsigned/unknown boot image
via `fastboot boot`. It never touches flash.

    python make-test-bootimg.py stock_boot.img test.img
    python make-test-bootimg.py stock_boot.img test-noheader.img --no-kernel-header
"""
import argparse
import struct
import sys
from pathlib import Path

from bootimg import parse_boot_image

STUB_LOOP = bytes.fromhex("00000014")  # b .  (infinite loop)


def kernel_header(text_offset: int, image_size: int) -> bytes:
    """ARM64 Image header whose first instruction branches over the header."""
    header = bytearray(64)
    struct.pack_into("<I", header, 0, 0x14000010)  # b +0x40 -> payload
    struct.pack_into("<I", header, 4, 0x1400000F)  # unused
    struct.pack_into("<Q", header, 8, text_offset)
    struct.pack_into("<Q", header, 16, image_size)
    header[56:60] = b"ARM\x64"
    return bytes(header)


def pad(data: bytes, page: int) -> bytes:
    return data + b"\0" * ((-len(data)) % page)


def build_test_image(parsed: dict, output: Path, with_header: bool) -> None:
    raw = Path(parsed["path"]).read_bytes()
    header_version = parsed["header_version"]
    page = parsed["page_size"] if header_version <= 2 else 4096

    payload = STUB_LOOP
    if with_header:
        payload = kernel_header(parsed.get("kernel_addr") or 0, 64 + len(STUB_LOOP)) + STUB_LOOP

    header = bytearray(raw[:page])
    struct.pack_into("<I", header, 8, len(payload))  # kernel_size

    if header_version <= 2:
        struct.pack_into("<I", header, 16, 0)  # ramdisk_size
        struct.pack_into("<I", header, 24, 0)  # second_size
        if header_version >= 1:
            struct.pack_into("<I", header, 1632, 0)  # recovery_dtbo_size
        if header_version == 2:
            struct.pack_into("<I", header, 1648, 0)  # dtb_size
    else:
        struct.pack_into("<I", header, 12, 0)  # ramdisk_size
        if header_version == 4:
            struct.pack_into("<I", header, 1580, 0)  # signature_size

    output.write_bytes(bytes(header) + pad(payload, page))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stock", help="stock boot.img (used only as a header template)")
    parser.add_argument("output", help="test boot.img to write")
    parser.add_argument(
        "--no-kernel-header",
        action="store_true",
        help="omit the ARM64 Image header (use if ABL jumps without one)",
    )
    args = parser.parse_args()

    try:
        parsed = parse_boot_image(args.stock)
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1

    output = Path(args.output)
    build_test_image(parsed, output, with_header=not args.no_kernel_header)

    print(f"wrote {output} ({output.stat().st_size} bytes)")
    print(f"header_version {parsed['header_version']}, page {parsed['page_size']:#x}")
    print(f"kernel address {parsed.get('kernel_addr') or 'not in header'}")
    print("kernel payload: infinite loop" + ("" if args.no_kernel_header else " + ARM64 header"))
    print()
    print("This image is unsigned and does not boot an OS. Expect the device to hang;")
    print("power-cycle it to return to Android. Never flash it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
