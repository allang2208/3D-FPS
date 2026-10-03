"""Inventory the literal /Game asset paths declared in the weapon family headers.

The preloader has to cover every asset a runtime weapon switch can pull in, so it
helps to know how much is statically declared rather than discovered at runtime.

Usage: python scan_weapon_asset_paths.py [--root Source/FPSGAME]
"""

import argparse
import collections
import re
from pathlib import Path

PATTERN = re.compile(r'TEXT\(\s*"(/Game/[^"]+)"')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="Source/FPSGAME")
    args = ap.parse_args()

    root = Path(args.root)
    per_file = collections.Counter()
    all_paths = set()
    for path in sorted(root.rglob("*.h")):
        text = path.read_text(encoding="utf-8", errors="replace")
        hits = PATTERN.findall(text)
        if hits:
            per_file[path.name] = len(hits)
            all_paths.update(hits)

    for name, count in per_file.most_common(20):
        print(f"{name:42} {count:4d}")
    print(f"\nfiles with literal /Game paths : {len(per_file)}")
    print(f"distinct literal /Game paths   : {len(all_paths)}")

    # Group by the top-level content folder so the shape of the set is visible.
    groups = collections.Counter()
    for item in all_paths:
        parts = item.split("/")
        folder = "/".join(parts[1:3]) if len(parts) > 2 else item
        groups[folder] += 1
    print("\ntop folders:")
    for folder, count in groups.most_common(25):
        print(f"  {folder:44} {count:4d}")


if __name__ == "__main__":
    main()