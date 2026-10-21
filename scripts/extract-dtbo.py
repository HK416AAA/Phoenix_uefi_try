#!/usr/bin/env python3
"""Extract every FDT inside the `dtb` field of an Android boot image.

Huawei ships a DTBO table (magic 0xd7b7ab1e) containing a base DTB and
overlays. This tool does not need to understand the table header: it scans
for FDT magic and uses each blob's totalsize.

    python extract-dtbo.py stock_boot.img -o dtb-out
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

from bootimg import parse_boot_image

FDT_MAGIC = b"\xd0\x0d\xfe\xed"
DTBO_MAGIC = b"\xd7\xb7\xab\x1e"


def align_up(value: int, page: int) -> int:
    return (value + page - 1) // page * page


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image")
    parser.add_argument("-o", "--out", default="dtb-out")
    parser.add_argument("--index", type=int, default=None,
                        help="only extract the Nth FDT in file order (0-based)")
    parser.add_argument("--list", action="store_true", help="list FDTs without writing")
    args = parser.parse_args()

    try:
        info = parse_boot_image(args.image)
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1

    if info["header_version"] > 2:
        print("FAIL: only boot header v0-v2 carries a dtb field", file=sys.stderr)
        return 1

    page = info["page_size"]
    raw = Path(args.image).read_bytes()
    dtb_off = page + align_up(info["kernel_size"], page) + align_up(info["ramdisk_size"], page) \
        + align_up(info.get("second_size", 0), page)
    dtb_size = info.get("dtb_size") or 0
    blob = raw[dtb_off:dtb_off + dtb_size]

    if not blob:
        print("FAIL: dtb_size is zero", file=sys.stderr)
        return 1
    print(f"dtb field : {dtb_off:#x} + {dtb_size:#x}")
    print(f"magic     : {blob[:4].hex()} "
          f"({'DTBO table' if blob[:4] == DTBO_MAGIC else 'FDT' if blob[:4] == FDT_MAGIC else 'unknown'})")

    found: list[tuple[int, int]] = []
    pos = 0
    while True:
        pos = blob.find(FDT_MAGIC, pos)
        if pos == -1:
            break
        if pos + 8 > len(blob):
            break
        total = struct.unpack_from(">I", blob, pos + 4)[0]
        if 0 < total <= len(blob) - pos:
            found.append((pos, total))
            pos += total
        else:
            print(f"  skip bogus FDT at {pos:#x}: totalsize {total:#x}", file=sys.stderr)
            pos += 4

    if not found:
        print("FAIL: no FDT found in the dtb field", file=sys.stderr)
        return 1

    print(f"found {len(found)} FDT blob(s)")
    if args.list:
        for index, (pos, total) in enumerate(found):
            print(f"  [{index}] offset {pos:#x} totalsize {total:#x}")
        return 0

    if args.index is not None:
        if not 0 <= args.index < len(found):
            print(f"FAIL: --index {args.index} out of range 0-{len(found) - 1}", file=sys.stderr)
            return 1
        selected = [(args.index, found[args.index])]
    else:
        selected = list(enumerate(found))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for index, (pos, total) in selected:
        path = out / f"fdt_{index:04d}_{pos:06x}.dtb"
        path.write_bytes(blob[pos:pos + total])
        print(f"  [{index}] {path}  totalsize {total:#x} ({total})")

    print(f"extracted {len(selected)} FDT blob(s) into {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
