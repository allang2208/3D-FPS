"""Dump a window of named columns across frames, for rhythm hunting.

Usage: python column_window.py <csv> --columns A,B,C [--from 60] [--to 300]
                                                     [--step 1] [--trim-width 44]
"""

import argparse
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--columns", required=True)
    ap.add_argument("--from", dest="start", type=int, default=0)
    ap.add_argument("--to", dest="end", type=int, default=200)
    ap.add_argument("--step", type=int, default=1)
    args = ap.parse_args()

    lines = Path(args.csv).read_text(encoding="utf-8", errors="replace").split("\n")
    header = lines[0].split(",")
    width = len(header)
    wanted = args.columns.split(",")
    indices = []
    for name in wanted:
        if name not in header:
            print(f"missing column: {name}", file=sys.stderr)
            return 1
        indices.append(header.index(name))

    rows = []
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split(",")
        if len(parts) < width:
            continue
        try:
            float(parts[indices[0]])
        except ValueError:
            continue
        rows.append(parts)

    header_cells = [n.split("/")[-1][:11] for n in wanted]
    print(f"{'frame':>6} " + " ".join(f"{c:>11}" for c in header_cells))
    for index in range(args.start, min(args.end, len(rows)), args.step):
        cells = []
        for column in indices:
            try:
                cells.append(f"{float(rows[index][column]):>11.2f}")
            except (ValueError, IndexError):
                cells.append(f"{'?':>11}")
        print(f"{index:>6} " + " ".join(cells))
    return 0


if __name__ == "__main__":
    sys.exit(main())