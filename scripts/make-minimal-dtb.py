#!/usr/bin/env python3
"""Generate a minimal device tree for the TAS UEFI build.

Contents:
  /memory          0x0..0x10000000
  /psci            arm,psci + method = "hvc"
  /simple-framebuffer  logo buffer at 0x36500000 (1080x2340, 32bpp)
  /chosen          bootargs
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

FDT_MAGIC = 0xD00DFEED
FDT_BEGIN_NODE = 1
FDT_END_NODE = 2
FDT_PROP = 3
FDT_END = 9


def align4(data: bytearray) -> None:
    while len(data) % 4:
        data.append(0)


class Builder:
    def __init__(self) -> None:
        self.struct = bytearray()
        self.strings = bytearray()
        self.offsets: dict[str, int] = {}

    def _name(self, name: str) -> int:
        if name not in self.offsets:
            self.offsets[name] = len(self.strings)
            self.strings.extend(name.encode() + b"\0")
        return self.offsets[name]

    def begin(self, name: str) -> None:
        self.struct.extend(struct.pack(">I", FDT_BEGIN_NODE))
        self.struct.extend(name.encode() + b"\0")
        align4(self.struct)

    def end(self) -> None:
        self.struct.extend(struct.pack(">I", FDT_END_NODE))

    def prop(self, name: str, value: bytes) -> None:
        self.struct.extend(struct.pack(">III", FDT_PROP, len(value), self._name(name)))
        self.struct.extend(value)
        align4(self.struct)

    def prop_u32(self, name: str, *values: int) -> None:
        self.prop(name, b"".join(struct.pack(">I", v) for v in values))

    def prop_str(self, name: str, value: str) -> None:
        self.prop(name, value.encode() + b"\0")

    def finish(self) -> bytes:
        self.struct.extend(struct.pack(">I", FDT_END))
        off_rsvmap = 40
        off_struct = off_rsvmap + 16
        off_strings = off_struct + len(self.struct)
        total = off_strings + len(self.strings)
        header = struct.pack(
            ">10I",
            FDT_MAGIC,
            total,
            off_struct,
            off_strings,
            off_rsvmap,
            17,
            16,
            0,
            len(self.strings),
            len(self.struct),
        )
        return header + b"\0" * 16 + bytes(self.struct) + bytes(self.strings)


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "tas.dtb")

    b = Builder()
    b.begin("")
    b.prop_u32("#address-cells", 2)
    b.prop_u32("#size-cells", 2)
    b.prop_str("model", "Huawei Mate 30 (TAS-AL00)")
    b.prop_str("compatible", "huawei,tas-al00")

    b.begin("memory@0")
    b.prop_str("device_type", "memory")
    b.prop_u32("reg", 0, 0x00000000, 0, 0x10000000)
    b.end()

    b.begin("psci")
    b.prop_str("compatible", "arm,psci")
    b.prop_str("method", "hvc")
    b.prop_u32("cpu_suspend", 0xC4000001)
    b.prop_u32("cpu_off", 0x84000002)
    b.prop_u32("cpu_on", 0xC4000003)
    b.end()

    b.begin("simple-framebuffer")
    b.prop_str("compatible", "simple-framebuffer")
    b.prop_str("status", "okay")
    b.prop_u32("reg", 0, 0x36500000, 0, 0x03F00000)
    b.prop_u32("width", 1080)
    b.prop_u32("height", 2340)
    b.prop_u32("stride", 1080 * 4)
    b.prop_str("format", "a8r8g8b8")
    b.end()

    b.begin("chosen")
    b.prop_str("bootargs", "console=tty0")
    b.end()

    b.end()

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(b.finish())
    print(f"wrote {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
