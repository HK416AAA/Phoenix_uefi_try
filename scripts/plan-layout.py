#!/usr/bin/env python3
"""Compute a safe UEFI FD layout for a device.

Inputs:
  * the boot.img you already flash (for kernel_addr / ramdisk_addr / page_size)
  * the runtime DTS dumped from /proc/device-tree

Output:
  * a human-readable memory map
  * a TOML fragment for Resources/Configs/<device>.toml

    python plan-layout.py --boot boot.img --dts runtime.dts
    python plan-layout.py --boot boot.img --dts runtime.dts --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from bootimg import parse_boot_image

ALIGN = 4 * 1024 * 1024
MARGIN = 1024 * 1024
DEFAULT_FD_SIZE = 3 * 1024 * 1024
FOUR_GB = 0x1_0000_0000


class Node:
    def __init__(self, name: str):
        self.name = name
        self.props: dict[str, str | None] = {}
        self.children: list[Node] = []


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    return text


def parse_dts(text: str) -> Node:
    text = strip_comments(text)
    root = Node("/")
    stack = [root]
    buf: list[str] = []

    for ch in text:
        if ch == "{":
            name = "".join(buf).strip()
            buf = []
            if ":" in name:
                name = name.split(":", 1)[1].strip()
            if name == "/" and stack[-1] is root:
                node = root
            else:
                node = Node(name)
                stack[-1].children.append(node)
            stack.append(node)
        elif ch == "}":
            buf = []
            if len(stack) > 1:
                stack.pop()
        elif ch == ";":
            stmt = "".join(buf).strip()
            buf = []
            if not stmt or stmt in ("/dts-v1/", "/plugin/"):
                continue
            if "=" in stmt:
                key, value = stmt.split("=", 1)
                stack[-1].props[key.strip()] = value.strip()
            else:
                stack[-1].props[stmt] = None
        else:
            buf.append(ch)
    return root


def prop_int(node: Node, name: str, default: int) -> int:
    value = node.props.get(name)
    if not value:
        return default
    digits = re.findall(r"0x[0-9a-fA-F]+|\b\d+\b", value)
    return int(digits[0], 0) if digits else default


def prop_cells(node: Node, name: str) -> list[int]:
    value = node.props.get(name)
    if not value:
        return []
    inner = value
    if inner.startswith("<"):
        inner = inner[1:inner.rfind(">")]
    return [int(token, 0) for token in re.findall(r"0x[0-9a-fA-F]+|\b\d+\b", inner)]


def reg_ranges(node: Node, addr_cells: int, size_cells: int) -> list[tuple[int, int]]:
    cells = prop_cells(node, "reg")
    entry = addr_cells + size_cells
    if not cells or len(cells) < entry:
        return []
    ranges = []
    for offset in range(0, len(cells) - entry + 1, entry):
        addr = 0
        for cell in cells[offset:offset + addr_cells]:
            addr = (addr << 32) | cell
        size = 0
        for cell in cells[offset + addr_cells:offset + entry]:
            size = (size << 32) | cell
        if size:
            ranges.append((addr, addr + size))
    return ranges


def find_child(node: Node, name: str) -> Node | None:
    for child in node.children:
        if child.name == name:
            return child
    return None


def subtract(ranges: list[tuple[int, int]], holes: list[tuple[int, int]]) -> list[tuple[int, int]]:
    result = list(ranges)
    for hole_start, hole_end in holes:
        pieces = []
        for start, end in result:
            if hole_end <= start or hole_start >= end:
                pieces.append((start, end))
                continue
            if start < hole_start:
                pieces.append((start, hole_start))
            if hole_end < end:
                pieces.append((hole_end, end))
        result = pieces
    return result


def align_up(value: int, alignment: int) -> int:
    return (value + alignment - 1) // alignment * alignment


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--boot", required=True, help="boot.img already known to boot")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--dts", help="runtime.dts from /proc/device-tree")
    source.add_argument("--dtb", help="FDT/DTB blob (for example extracted from the boot image)")
    parser.add_argument("--fd-size", default=hex(DEFAULT_FD_SIZE))
    parser.add_argument("--kernel-base", default=None,
                        help="actual physical kernel base from /proc/iomem (overrides the boot header)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        boot = parse_boot_image(args.boot, inspect_image=True)
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1

    try:
        fd_size = int(args.fd_size, 0)
    except ValueError:
        print(f"FAIL: bad --fd-size {args.fd_size}", file=sys.stderr)
        return 1

    if args.dtb:
        from fdt import iter_nodes, parse_fdt, reg_ranges as fdt_reg_ranges

        fdt = parse_fdt(args.dtb)
        memory: list[tuple[int, int]] = []
        reserved: list[tuple[int, int]] = [
            (addr, addr + size) for addr, size in fdt.reservations if size
        ]
        for node, path, ac, sc in iter_nodes(fdt.root):
            if node.name == "memory" or node.name.startswith("memory@"):
                memory.extend(fdt_reg_ranges(node, ac, sc))
            elif path.startswith("/reserved-memory/") and node.has("reg"):
                reserved.extend(fdt_reg_ranges(node, ac, sc))
    else:
        dts_text = Path(args.dts).read_text(encoding="utf-8", errors="replace")
        root = parse_dts(dts_text)
        addr_cells = prop_int(root, "#address-cells", 2)
        size_cells = prop_int(root, "#size-cells", 2)

        memory = []
        for child in root.children:
            if child.name == "memory" or child.name.startswith("memory@"):
                memory.extend(reg_ranges(child, addr_cells, size_cells))

        reserved = []
        reserved_node = find_child(root, "reserved-memory")
        if reserved_node:
            for child in reserved_node.children:
                reserved.extend(reg_ranges(child, addr_cells, size_cells))

    if not memory:
        print("FAIL: no /memory node found in the DTS", file=sys.stderr)
        return 1

    kernel_addr = int(args.kernel_base, 0) if args.kernel_base else boot.get("kernel_addr")
    if kernel_addr is None:
        print("FAIL: boot header v3/v4 has no kernel_addr; use --kernel-base", file=sys.stderr)
        return 1

    # image_size includes BSS. gzip's ISIZE only covers the file, so it
    # underestimates the real footprint by several MiB.
    arm = boot.get("arm64") or {}
    kernel_footprint = arm.get("image_size") or boot.get("kernel_uncompressed_size") or boot["kernel_size"]
    kernel = [(kernel_addr, kernel_addr + kernel_footprint)]
    ramdisk = []
    if boot.get("ramdisk_addr") and boot.get("ramdisk_size"):
        ramdisk = [(boot["ramdisk_addr"], boot["ramdisk_addr"] + boot["ramdisk_size"])]
    tags = []
    if boot.get("tags_addr"):
        tags = [(boot["tags_addr"], boot["tags_addr"] + 2 * 1024 * 1024)]

    blocked = reserved + kernel + ramdisk + tags
    free = subtract(memory, blocked)

    kernel_end = kernel[0][1]
    candidate = None
    for start, end in sorted(free):
        point = align_up(max(start, kernel_end + MARGIN), ALIGN)
        if point + fd_size <= end:
            candidate = point
            break

    report = {
        "boot": {
            "kernel_addr": kernel_addr,
            "kernel_size": boot["kernel_size"],
            "kernel_footprint": kernel_footprint,
            "kernel_end": kernel_end,
            "arm64": arm,
            "ramdisk_addr": boot.get("ramdisk_addr"),
            "ramdisk_size": boot.get("ramdisk_size"),
            "tags_addr": boot.get("tags_addr"),
            "page_size": boot.get("page_size"),
            "header_version": boot.get("header_version"),
        },
        "memory": memory,
        "reserved": reserved,
        "free": free,
        "fd": {"base": candidate, "size": fd_size},
    }

    if candidate is None:
        print("FAIL: no free window can hold the FD", file=sys.stderr)
        for start, end in free:
            print(f"  free {start:#x}-{end:#x} ({(end - start) >> 20} MiB)", file=sys.stderr)
        return 1

    warnings = []
    if not args.kernel_base:
        warnings.append("kernel base assumed from the boot header; "
                        "confirm with `adb shell cat /proc/iomem` (Kernel code)")
    if arm and not arm.get("pie"):
        warnings.append("kernel Image is not PIE; it must load at text_offset + base")
    if candidate + fd_size > FOUR_GB:
        warnings.append("FD sits above 4 GiB; keep the first attempt below 4 GiB if possible")
    if candidate < kernel_end:
        warnings.append("FD base is below the kernel end; this should not happen")
    report["warnings"] = warnings

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print(f"kernel       : {kernel_addr:#x} - {kernel_end:#x} "
          f"(stored {boot['kernel_size']:#x}, footprint {kernel_footprint:#x})")
    if arm:
        print(f"image header : text_offset={arm['text_offset']:#x} "
              f"image_size={arm['image_size']:#x} PIE={arm['pie']} 4K={arm['four_k_pages']}")
    if ramdisk:
        print(f"ramdisk      : {ramdisk[0][0]:#x} - {ramdisk[0][1]:#x}")
    if tags:
        print(f"tags/dtb     : {tags[0][0]:#x} - {tags[0][1]:#x} (assumed 2 MiB)")
    print("memory       :")
    for start, end in memory:
        print(f"  {start:#010x} - {end:#010x}  {(end - start) >> 20} MiB")
    print("reserved     :")
    for start, end in reserved:
        print(f"  {start:#010x} - {end:#010x}  {(end - start) >> 20} MiB")
    print("free windows :")
    for start, end in free:
        print(f"  {start:#010x} - {end:#010x}  {(end - start) >> 20} MiB")
    print()
    print(f"FD_BASE      : {candidate:#x}")
    print(f"FD_SIZE      : {fd_size:#x}")
    if warnings:
        print()
        for warning in warnings:
            print(f"WARN: {warning}")
    print()
    print("# Resources/Configs/tas.toml (check field names against a known-good device)")
    print("[uefi_fd]")
    print(f"base = {candidate:#x}")
    print(f"size = {fd_size:#x}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
