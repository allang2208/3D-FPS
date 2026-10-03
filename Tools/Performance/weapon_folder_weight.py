"""How much of the weapon asset tree is dead revision content?

The preloader's folder expansion swept far more packages than the game ever loads.
The weapon folders keep every design revision (SightGrip, Recovery07, GripFinish08,
...), and only the newest one is referenced by the family constants. This measures
that ratio so the expansion scope is chosen from evidence.

Usage: python weapon_folder_weight.py [--root Content/Weapons]
"""

import argparse
from collections import Counter
from pathlib import Path

# Extensions that are real loadable assets rather than source or sidecar files.
ASSET_SUFFIX = {".uasset", ".umap"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="Content/Weapons")
    ap.add_argument("--top", type=int, default=18)
    args = ap.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        raise SystemExit(f"not a directory: {root}")

    # Package = the .uasset file; a family folder is the level below the weapon folder.
    families = Counter()
    revisions = Counter()
    total = 0
    for path in root.rglob("*"):
        if path.suffix not in ASSET_SUFFIX:
            continue
        total += 1
        rel = path.relative_to(root).parts
        if len(rel) >= 2:
            family = rel[0]
            families[family] += 1
            if len(rel) >= 3:
                revisions[(family, rel[1])] += 1
            else:
                revisions[(family, "<root>")] += 1
        else:
            families["<root>"] += 1

    print(f"total packages under {root}: {total}")
    print("\nby weapon family:")
    for family, count in families.most_common(args.top):
        print(f"  {family:32} {count:5d}")

    print("\nby revision folder (top 30) -- only the newest of each is referenced:")
    for (family, rev), count in revisions.most_common(30):
        print(f"  {family + '/' + rev:60} {count:5d}")


if __name__ == "__main__":
    main()