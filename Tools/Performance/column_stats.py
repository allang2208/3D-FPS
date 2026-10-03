"""Column statistics across all usable frames of a capture (no editor needed).

Usage: python column_stats.py <capture.csv> [--tail N] [--cols a,b,c]

Prints mean/p50/p90/max and the number of frames with a non-zero value for each
requested column (or every column whose max exceeds --min-max when none are
requested). Useful for telling "happens every frame" from "happens on hitches".
"""

import argparse
import statistics
import sys
from pathlib import Path


def read_header(lines):
    for line in lines[:5]:
        fields = line.split(",")
        if fields[0] == "EVENTS" and "FrameTime" in fields:
            return fields
    sys.exit("no header line (first column EVENTS) found")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--tail", type=int, default=0, help="only the last N usable frames")
    ap.add_argument("--skip", type=int, default=10)
    ap.add_argument("--cols", default=None, help="comma separated column names")
    ap.add_argument("--min-max", type=float, default=1.0)
    ap.add_argument("--report")
    args = ap.parse_args()

    lines = Path(args.csv).read_text(encoding="utf-8", errors="replace").split("\n")
    header = read_header(lines)
    width = len(header)
    ft_idx = header.index("FrameTime")

    rows = []
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split(",")
        if len(parts) < width:
            continue
        try:
            if float(parts[ft_idx]) <= 0:
                continue
        except ValueError:
            continue
        rows.append(parts)

    rows = rows[args.skip:]
    if args.tail:
        rows = rows[-args.tail:]
    print(f"frames analysed: {len(rows)}")

    if args.cols:
        names = [c.strip() for c in args.cols.split(",") if c.strip()]
    else:
        names = []
        for k, name in enumerate(header):
            values = []
            for r in rows:
                try:
                    values.append(float(r[k]))
                except ValueError:
                    pass
            if values and max(values) >= args.min_max:
                names.append(name)
                continue
        print(f"columns with max >= {args.min_max}: {len(names)}")

    out = []
    out.append(f"frames analysed: {len(rows)}")
    out.append(f"{'column':<56}{'mean':>12}{'p50':>12}{'p90':>12}{'max':>12}{'nonzero':>9}")
    for name in names:
        if name not in header:
            out.append(f"{name:<56}{'MISSING':>12}")
            continue
        k = header.index(name)
        values = []
        for r in rows:
            try:
                values.append(float(r[k]))
            except ValueError:
                pass
        if not values:
            continue
        ordered = sorted(values)
        p50 = ordered[len(ordered) // 2]
        p90 = ordered[int(len(ordered) * 0.9)]
        nonzero = sum(1 for v in values if v > 0)
        out.append(f"{name:<56}{statistics.fmean(values):12.3f}{p50:12.3f}"
                   f"{p90:12.3f}{ordered[-1]:12.3f}{nonzero:9d}")

    text = "\n".join(out)
    print(text)
    if args.report:
        Path(args.report).write_text(text, encoding="utf-8")
        print(f"[written] {args.report}")


if __name__ == "__main__":
    main()