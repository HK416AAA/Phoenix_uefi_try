#!/usr/bin/env python3
"""Insert a pmsg checkpoint at the start of BdsEntry()."""
from __future__ import annotations

import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: patch-bds-entry.py <BdsEntry.c>")
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"not found: {path}")
        return 0

    text = path.read_text(encoding="utf-8")
    text, count = re.subn(
        r"(BdsEntry\s*\([^)]*\)\s*\{)",
        r'\1\n  DEBUG ((DEBUG_ERROR, "TAS-BDS-ENTRY\\n"));',
        text,
        count=1,
    )
    if count:
        path.write_text(text, encoding="utf-8")
    print(f"bds-entry patch: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
