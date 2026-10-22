#!/usr/bin/env python3
"""Delete old boot-*.img files, keeping only the newest one."""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", help="image name to keep; defaults to the newest boot-*.img")
    parser.add_argument("--root", default=".")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    images = sorted(
        root.glob("boot-*.img"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not images:
        print("no boot-*.img found")
        return 0

    keep = Path(args.keep).name if args.keep else images[0].name
    removed = []
    for path in images:
        if path.name == keep:
            continue
        if not args.dry_run:
            path.unlink()
        removed.append(path.name)

    print(f"keep: {keep}")
    action = "would remove" if args.dry_run else "removed"
    print(f"{action}: {', '.join(removed) if removed else 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
