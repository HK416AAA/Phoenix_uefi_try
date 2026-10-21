#!/usr/bin/env python3
"""Parse Android boot images (header v0-v4) and report load addresses.

Usage:
    python bootimg.py stock_boot.img
    python bootimg.py stock_boot.img --json
"""
from __future__ import annotations

import argparse
import gzip
import json
import struct
import sys
from pathlib import Path

BOOT_MAGIC = b"ANDROID!"
VENDOR_BOOT_MAGIC = b"VNDRBOOT"


def u32(buf: bytes, off: int) -> int:
    return struct.unpack_from("<I", buf, off)[0]


def u64(buf: bytes, off: int) -> int:
    return struct.unpack_from("<Q", buf, off)[0]


def cstr(buf: bytes, off: int, size: int) -> str:
    return buf[off:off + size].split(b"\0", 1)[0].decode("utf-8", "replace")


def decode_os_version(value: int) -> str:
    major = (value >> 29) & 0x7F
    minor = (value >> 22) & 0x7F
    patch = (value >> 11) & 0x7F
    year = (value >> 0) & 0x7F
    text = f"{major}.{minor}.{patch}"
    if year:
        text += f" (year {2000 + year})"
    return text


def detect_payload(data: bytes) -> str:
    if data[:2] == b"\x1f\x8b":
        return "gzip"
    if data[:4] == b"\x04\x22\x4d\x18":
        return "lz4"
    if data[:6] == b"\xfd7zXZ\x00":
        return "xz"
    if len(data) >= 0x3C and data[0x38:0x3C] == b"ARM\x64":
        return "arm64-image"
    if b"zImage" in data[:0x30]:
        return "zimage"
    return "raw"


def read_arm64_image(payload: bytes) -> dict | None:
    """Read the ARM64 Image header, decompressing gzip if needed."""
    image = payload
    if payload[:2] == b"\x1f\x8b":
        try:
            image = gzip.decompress(payload)
        except OSError:
            return None
    if len(image) < 64 or image[56:60] != b"ARM\x64":
        return None
    text_offset, image_size, flags = struct.unpack_from("<QQQ", image, 8)
    return {
        "text_offset": text_offset,
        "image_size": image_size,
        "flags": flags,
        "pie": bool(flags & 0x8),
        "four_k_pages": bool(flags & 0x2),
        "file_size": len(image),
    }


def parse_boot_image(path: str | Path, inspect_image: bool = False) -> dict:
    path = Path(path)
    data = path.read_bytes()
    if len(data) < 48:
        raise ValueError(f"{path} is too small to be a boot image")

    magic = data[:8]
    if magic == VENDOR_BOOT_MAGIC:
        raise ValueError(f"{path} is a vendor_boot image, not supported")
    if magic != BOOT_MAGIC:
        raise ValueError(f"{path} has bad magic {magic!r}, expected {BOOT_MAGIC!r}")

    header_version = u32(data, 40)
    info: dict = {
        "path": str(path),
        "file_size": len(data),
        "header_version": header_version,
    }

    if header_version in (0, 1, 2):
        page_size = u32(data, 36)
        if page_size not in (2048, 4096, 8192, 16384, 65536):
            raise ValueError(f"implausible page_size {page_size:#x}")
        info.update({
            "page_size": page_size,
            "kernel_size": u32(data, 8),
            "kernel_addr": u32(data, 12),
            "ramdisk_size": u32(data, 16),
            "ramdisk_addr": u32(data, 20),
            "second_size": u32(data, 24),
            "second_addr": u32(data, 28),
            "tags_addr": u32(data, 32),
            "os_version": decode_os_version(u32(data, 44)),
            "name": cstr(data, 48, 16),
            "cmdline": cstr(data, 64, 512),
            "kernel_offset": page_size,
        })
        if header_version >= 1:
            info.update({
                "recovery_dtbo_size": u32(data, 1632),
                "recovery_dtbo_offset": u64(data, 1636),
                "header_size": u32(data, 1644),
            })
        if header_version == 2:
            info.update({
                "dtb_size": u32(data, 1648),
                "dtb_addr": u64(data, 1652),
            })
    elif header_version in (3, 4):
        info.update({
            "page_size": 4096,
            "kernel_size": u32(data, 8),
            "ramdisk_size": u32(data, 12),
            "os_version": decode_os_version(u32(data, 16)),
            "header_size": u32(data, 20),
            "cmdline": cstr(data, 44, 1536),
            "kernel_offset": 4096,
            "kernel_addr": None,
            "ramdisk_addr": None,
            "tags_addr": None,
        })
        if header_version == 4:
            info["signature_size"] = u32(data, 1580)
    else:
        raise ValueError(f"unsupported boot header version {header_version}")

    start = info["kernel_offset"]
    end = start + info["kernel_size"]
    payload = data[start:end]
    info["kernel_magic"] = detect_payload(payload)
    if info["kernel_magic"] == "gzip" and len(payload) >= 18:
        # ISIZE of the last gzip member: uncompressed size modulo 2^32.
        info["kernel_uncompressed_size"] = struct.unpack_from("<I", payload, len(payload) - 4)[0]
    if inspect_image:
        info["arm64"] = read_arm64_image(payload)
    info["kernel_offset_hex"] = hex(start)
    info["kernel_end"] = hex(end)
    info["load_range"] = (
        f"{info['kernel_addr']:#x}-{info['kernel_addr'] + info['kernel_size']:#x}"
        if info.get("kernel_addr") else None
    )
    return info


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--extract-kernel", metavar="PATH",
                        help="write the kernel payload (still compressed) to PATH")
    parser.add_argument("--inspect-image", action="store_true",
                        help="decompress and read the ARM64 Image header (image_size, flags)")
    args = parser.parse_args()

    try:
        info = parse_boot_image(args.image, inspect_image=args.inspect_image)
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1

    if args.extract_kernel:
        start = info["kernel_offset"]
        payload = Path(args.image).read_bytes()[start:start + info["kernel_size"]]
        Path(args.extract_kernel).write_bytes(payload)
        print(f"wrote {args.extract_kernel} ({len(payload)} bytes, {info['kernel_magic']})")

    if args.json:
        print(json.dumps(info, indent=2, ensure_ascii=False))
        return 0

    for key in (
        "path", "file_size", "header_version", "page_size",
        "kernel_size", "kernel_addr", "kernel_magic", "kernel_offset_hex",
        "ramdisk_size", "ramdisk_addr", "second_size", "tags_addr",
        "os_version", "cmdline", "load_range",
    ):
        if key in info and info[key] is not None:
            value = info[key]
            if isinstance(value, int) and key not in ("file_size", "kernel_size", "ramdisk_size", "second_size", "header_version", "page_size"):
                value = f"{value:#x}"
            print(f"{key:16}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
