#!/usr/bin/env python3
"""Replace the kernel in a Huawei (boot header v2) image, keeping its DTBO table.

Huawei's `dtb` field is not a single FDT: it is an Android DTBO table
(magic 0xd7b7ab1e) containing a base DTB plus overlays. Rewriting it as a
single appended DTB breaks the boot, so this tool copies the original table
byte for byte and only swaps the kernel (and optionally the ramdisk).

    python repack-bootimg.py --stock stock.img --kernel Image.gz --out new.img
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

from bootimg import parse_boot_image

DTBO_MAGIC = b"\xd7\xb7\xab\x1e"
FDT_MAGIC = b"\xd0\x0d\xfe\xed"


def align_up(value: int, page: int) -> int:
    return (value + page - 1) // page * page


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stock", required=True, help="stock boot.img used as the template")
    parser.add_argument("--kernel", required=True, help="new kernel blob (gzip unless --no-gzip-check)")
    parser.add_argument("--ramdisk", help="optional new ramdisk blob")
    parser.add_argument("--out", required=True)
    parser.add_argument("--no-gzip-check", action="store_true")
    parser.add_argument("--cmdline-append", default=None,
                        help="append to the v2 cmdline, e.g. log_buf_len=8M")
    parser.add_argument("--keep-tail", action="store_true",
                        help="preserve the original bytes after the DTBO (AVB footer/signature)")
    parser.add_argument("--pad-to", default=None,
                        help="pad output with zeros (default: stock file size, overwrites stale AVB tails)")
    args = parser.parse_args()

    try:
        stock = parse_boot_image(args.stock)
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1

    if stock["header_version"] != 2:
        print(f"FAIL: need boot header v2, got v{stock['header_version']}", file=sys.stderr)
        return 1

    page = stock["page_size"]
    raw = Path(args.stock).read_bytes()

    kernel_off = page
    ramdisk_off = kernel_off + align_up(stock["kernel_size"], page)
    second_off = ramdisk_off + align_up(stock["ramdisk_size"], page)
    dtb_off = second_off + align_up(stock.get("second_size", 0), page)
    dtb_size = stock.get("dtb_size") or 0
    dtb = raw[dtb_off:dtb_off + dtb_size]

    if dtb_size and dtb[:4] not in (DTBO_MAGIC, FDT_MAGIC):
        print(f"FAIL: no DTBO/FDT magic at {dtb_off:#x}: {dtb[:4].hex()}", file=sys.stderr)
        return 1

    kernel = Path(args.kernel).read_bytes()
    if not args.no_gzip_check and kernel[:2] != b"\x1f\x8b":
        print("FAIL: kernel is not gzip (use --no-gzip-check to override)", file=sys.stderr)
        return 1

    if args.ramdisk:
        ramdisk = Path(args.ramdisk).read_bytes()
    else:
        ramdisk = raw[ramdisk_off:ramdisk_off + stock["ramdisk_size"]]

    header = bytearray(raw[:page])
    struct.pack_into("<I", header, 8, len(kernel))       # kernel_size
    struct.pack_into("<I", header, 16, len(ramdisk))     # ramdisk_size
    struct.pack_into("<I", header, 24, 0)                # second_size
    struct.pack_into("<I", header, 1648, len(dtb))       # dtb_size
    # kernel_addr / ramdisk_addr / tags_addr / dtb_addr stay untouched.

    if args.cmdline_append:
        old = bytes(header[64:576]).split(b"\0", 1)[0].decode("utf-8", "replace")
        new = (old + " " + args.cmdline_append).strip()
        encoded = new.encode("utf-8")
        if len(encoded) > 511:
            print(f"FAIL: cmdline would be {len(encoded)} bytes (max 511)", file=sys.stderr)
            return 1
        header[64:576] = encoded + b"\0" * (512 - len(encoded))
        print(f"cmdline     : {new}")

    def pad(data: bytes) -> bytes:
        return data + b"\0" * ((-len(data)) % page)

    out = bytes(header) + pad(kernel) + pad(ramdisk) + pad(dtb)
    pad_to = int(args.pad_to, 0) if args.pad_to else stock["file_size"]
    if len(out) > pad_to:
        print(f"FAIL: image is {len(out)} bytes, larger than --pad-to {pad_to}", file=sys.stderr)
        return 1
    out += b"\0" * (pad_to - len(out))

    tail = raw[dtb_off + dtb_size:] if args.keep_tail else b""
    if tail:
        if len(tail) > len(out):
            print(f"FAIL: tail is {len(tail)} bytes, larger than the image", file=sys.stderr)
            return 1
        out = out[:-len(tail)] + tail

    Path(args.out).write_bytes(out)

    new_dtb_off = page + align_up(len(kernel), page) + align_up(len(ramdisk), page)
    print(f"wrote       : {args.out} ({len(out)} bytes)")
    print(f"kernel      : {kernel_off:#x} + {len(kernel):#x} (gzip)")
    print(f"ramdisk     : {ramdisk_off:#x} + {len(ramdisk):#x}")
    print(f"dtb         : {new_dtb_off:#x} + {len(dtb):#x} "
          f"({'DTBO table' if dtb[:4] == DTBO_MAGIC else 'FDT' if dtb[:4] == FDT_MAGIC else 'empty'})")
    print(f"kernel_addr : {stock['kernel_addr']:#x}")
    print(f"ramdisk_addr: {stock['ramdisk_addr']:#x}")
    print(f"tags_addr   : {stock['tags_addr']:#x}")
    if stock.get("dtb_addr") is not None:
        print(f"dtb_addr    : {stock['dtb_addr']:#x} (unchanged)")
    if tail:
        print(f"tail        : preserved {len(tail)} bytes (AVB footer/signature)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
