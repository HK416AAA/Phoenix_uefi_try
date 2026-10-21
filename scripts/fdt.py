"""Minimal flattened device tree (FDT/DTB) reader.

Enough to extract memory, reserved-memory, psci, cpus, timer, GIC, serial,
ufs, pmic, gpio and ramoops from a vendor DTB without libfdt or dtc.
"""
from __future__ import annotations

import struct
from pathlib import Path

FDT_MAGIC = 0xD00DFEED
FDT_BEGIN_NODE = 1
FDT_END_NODE = 2
FDT_PROP = 3
FDT_NOP = 4
FDT_END = 9


class Node:
    __slots__ = ("name", "props", "children")

    def __init__(self, name: str):
        self.name = name
        self.props: dict[str, bytes] = {}
        self.children: list[Node] = []

    def strings(self, name: str) -> list[str]:
        value = self.props.get(name)
        if not value:
            return []
        return [part.decode("utf-8", "replace") for part in value.split(b"\0") if part]

    def string(self, name: str) -> str | None:
        values = self.strings(name)
        return values[0] if values else None

    def u32(self, name: str, index: int = 0, default: int | None = None) -> int | None:
        value = self.props.get(name)
        if not value or len(value) < (index + 1) * 4:
            return default
        return struct.unpack_from(">I", value, index * 4)[0]

    def cells(self, name: str) -> list[int]:
        value = self.props.get(name)
        if not value:
            return []
        count = len(value) // 4
        return list(struct.unpack_from(f">{count}I", value, 0))

    def has(self, name: str) -> bool:
        return name in self.props


class Fdt:
    def __init__(self, root: Node, reservations: list[tuple[int, int]], totalsize: int):
        self.root = root
        self.reservations = reservations
        self.totalsize = totalsize


def _cstr(data: bytes, pos: int) -> tuple[str, int]:
    end = data.index(b"\0", pos)
    return data[pos:end].decode("utf-8", "replace"), end + 1


def _align4(value: int) -> int:
    return (value + 3) & ~3


def parse_fdt_bytes(data: bytes) -> Fdt:
    if len(data) < 40:
        raise ValueError("blob is too small to be an FDT")
    (magic, totalsize, off_struct, off_strings, off_rsvmap,
     version, last_comp, boot_cpuid, size_strings, size_struct) = struct.unpack_from(">10I", data, 0)
    if magic != FDT_MAGIC:
        raise ValueError(f"bad FDT magic {magic:#x}")
    if totalsize > len(data):
        raise ValueError(f"FDT totalsize {totalsize:#x} exceeds blob {len(data):#x}")

    strings = data[off_strings:off_strings + size_strings]

    reservations: list[tuple[int, int]] = []
    pos = off_rsvmap
    while pos + 16 <= len(data):
        addr, size = struct.unpack_from(">QQ", data, pos)
        pos += 16
        if addr == 0 and size == 0:
            break
        reservations.append((addr, size))

    root = Node("/")
    stack = [root]
    pos = off_struct
    while pos + 4 <= len(data):
        token = struct.unpack_from(">I", data, pos)[0]
        pos += 4
        if token == FDT_BEGIN_NODE:
            name, pos = _cstr(data, pos)
            pos = _align4(pos)
            node = Node(name or "/")
            stack[-1].children.append(node)
            stack.append(node)
        elif token == FDT_END_NODE:
            if len(stack) > 1:
                stack.pop()
        elif token == FDT_PROP:
            length, nameoff = struct.unpack_from(">II", data, pos)
            pos += 8
            value = data[pos:pos + length]
            pos = _align4(pos + length)
            end = strings.index(b"\0", nameoff)
            name = strings[nameoff:end].decode("utf-8", "replace")
            stack[-1].props[name] = value
        elif token == FDT_NOP:
            continue
        elif token == FDT_END:
            break
        else:
            raise ValueError(f"unknown FDT token {token} at {pos - 4:#x}")

    return Fdt(root, reservations, totalsize)


def parse_fdt(path: str | Path) -> Fdt:
    return parse_fdt_bytes(Path(path).read_bytes())


def iter_nodes(node: Node, path: str = "", ac: int = 2, sc: int = 1):
    """Yield (node, path, parent_address_cells, parent_size_cells)."""
    if path in ("", "/"):
        current = "/" if node.name in ("/", "") else f"/{node.name}"
    else:
        current = f"{path.rstrip('/')}/{node.name}"
    yield node, current, ac, sc
    child_ac = node.u32("#address-cells", default=ac) or ac
    child_sc = node.u32("#size-cells", default=sc) or sc
    for child in node.children:
        yield from iter_nodes(child, current, child_ac, child_sc)


def reg_ranges(node: Node, ac: int, sc: int) -> list[tuple[int, int]]:
    cells = node.cells("reg")
    entry = ac + sc
    if not cells or entry <= 0 or len(cells) < entry:
        return []
    ranges = []
    for offset in range(0, len(cells) - entry + 1, entry):
        addr = 0
        for cell in cells[offset:offset + ac]:
            addr = (addr << 32) | cell
        size = 0
        for cell in cells[offset + ac:offset + entry]:
            size = (size << 32) | cell
        if size:
            ranges.append((addr, addr + size))
    return ranges


def find_nodes(fdt: Fdt, predicate) -> list[tuple[Node, str, int, int]]:
    return [item for item in iter_nodes(fdt.root) if predicate(item[0], item[1])]
