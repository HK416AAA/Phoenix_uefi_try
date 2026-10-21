#!/usr/bin/env python3
"""Print the board facts a UEFI port needs from a DTB.

    python dtb-info.py fdt_10b5860.dtb
    python dtb-info.py fdt_10b5860.dtb --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from fdt import Node, iter_nodes, parse_fdt, reg_ranges


def compat(node: Node) -> list[str]:
    return node.strings("compatible")


def regs(node: Node, ac: int, sc: int) -> list[str]:
    return [f"{a:#x}-{b:#x}" for a, b in reg_ranges(node, ac, sc)]


def irqs(node: Node) -> list[int]:
    return node.cells("interrupts")


def describe(node: Node, path: str, ac: int, sc: int) -> dict:
    item = {
        "path": path,
        "compatible": compat(node),
        "reg": regs(node, ac, sc),
        "interrupts": irqs(node),
    }
    for key in ("clock-frequency", "record-size", "status", "method"):
        if node.has(key):
            if key == "method":
                item[key] = node.string(key)
            else:
                item[key] = node.u32(key)
    return item


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dtb")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--grep", help="print nodes whose path or compatible matches this regex")
    args = parser.parse_args()

    try:
        fdt = parse_fdt(args.dtb)
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1

    nodes = list(iter_nodes(fdt.root))

    if args.grep:
        pattern = re.compile(args.grep, re.I)
        for node, path, ac, sc in nodes:
            text = f"{path} {' '.join(compat(node))}"
            if not pattern.search(text):
                continue
            print(path)
            print(f"  compatible: {', '.join(compat(node))}")
            print(f"  reg       : {regs(node, ac, sc)}")
            print(f"  interrupts: {irqs(node)}")
            for key in ("status", "clock-frequency", "record-size", "phandle", "memory-region"):
                if node.has(key):
                    value = node.u32(key) if key in ("clock-frequency", "record-size", "phandle") else node.string(key)
                    print(f"  {key:9} : {value}")
            print(f"  props     : {sorted(node.props)}")
        return 0

    report: dict = {
        "file": str(args.dtb),
        "totalsize": fdt.totalsize,
        "model": fdt.root.string("model"),
        "compatible": compat(fdt.root),
        "reservations": [f"{a:#x}+{s:#x}" for a, s in fdt.reservations],
        "memory": [],
        "reserved": [],
        "psci": [],
        "cpus": [],
        "timer": [],
        "gic": [],
        "serial": [],
        "ufs": [],
        "pmic": [],
        "gpio": [],
        "ramoops": [],
    }

    for node, path, ac, sc in nodes:
        name = node.name
        compat_list = compat(node)
        joined = " ".join(compat_list)

        if name.startswith("memory") or "memory" in compat_list:
            report["memory"].extend(regs(node, ac, sc))
        if path.startswith("/reserved-memory/") and node.has("reg"):
            report["reserved"].append(describe(node, path, ac, sc))
        if name == "psci":
            report["psci"].append(describe(node, path, ac, sc))
        if path.startswith("/cpus/") and name.startswith("cpu"):
            report["cpus"].append(describe(node, path, ac, sc))
        if name == "timer" or "arm,armv8-timer" in compat_list:
            report["timer"].append(describe(node, path, ac, sc))
        if "gic" in joined:
            report["gic"].append(describe(node, path, ac, sc))
        if name.startswith("serial") or any(k in joined for k in ("pl011", "8250", "dw-apb-uart", "hisi,uart")):
            report["serial"].append(describe(node, path, ac, sc))
        if "ufs" in name or "ufs" in joined:
            report["ufs"].append(describe(node, path, ac, sc))
        if "pmic" in joined or any(k in joined for k in ("hi6421", "hi6422")):
            report["pmic"].append(describe(node, path, ac, sc))
        if name.startswith("gpio"):
            report["gpio"].append(describe(node, path, ac, sc))
        if "ramoops" in joined:
            report["ramoops"].append(describe(node, path, ac, sc))

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    print(f"file       : {report['file']}")
    print(f"size       : {fdt.totalsize:#x}")
    print(f"model      : {report['model']}")
    print(f"compatible : {', '.join(report['compatible'])}")
    print(f"memreserve : {report['reservations']}")
    print(f"memory     : {report['memory']}")
    for key in ("reserved", "psci", "cpus", "timer", "gic", "serial", "ufs", "pmic", "gpio", "ramoops"):
        items = report[key]
        if not items:
            continue
        print(f"{key}:")
        for item in items[:12]:
            extra = ""
            if item["interrupts"]:
                extra += f" irq={item['interrupts']}"
            if item.get("clock-frequency"):
                extra += f" clk={item['clock-frequency']}"
            if item.get("method"):
                extra += f" method={item['method']}"
            if item.get("record-size"):
                extra += f" record={item['record-size']}"
            print(f"  {item['path']}")
            print(f"    compatible: {', '.join(item['compatible'])}")
            print(f"    reg       : {item['reg']}{extra}")
        if len(items) > 12:
            print(f"  ... {len(items) - 12} more")
    return 0


if __name__ == "__main__":
    sys.exit(main())
