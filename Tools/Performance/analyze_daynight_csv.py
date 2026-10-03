"""Analyse a UE CsvProfiler capture for hitch candidates.

Usage:
  python analyze_daynight_csv.py <capture.csv> [--skip N] [--top N] [--report out.txt]

The capture files written by this project are produced by CsvProfiler with
trace events prefixed to each record line, so records are aligned left after the
trace prefix and validated on FrameTime. Frames before --skip (engine start-up)
are excluded from the statistics but still reported separately.

Only reads the capture; it never runs the editor.
"""

import argparse
import statistics
import sys
from pathlib import Path


def split_record(line, width, ft_idx):
    """Return the CSV fields of one CsvProfiler record, or None when unusable.

    In these captures every record's first `width` fields are the schema columns
    in header order (the trace-event prefix is glued onto field 0), and some
    records carry extra trailing columns. Rows are therefore accepted by width
    and validated on a numeric FrameTime.
    """
    parts = line.split(",")
    if len(parts) < width:
        return None
    try:
        float(parts[ft_idx])
    except ValueError:
        return None
    return parts


def load(csv_path, skip):
    text = Path(csv_path).read_text(encoding="utf-8", errors="replace")
    lines = text.split("\n")
    header = None
    for line in lines[:5]:
        fields = line.split(",")
        if fields[0] == "EVENTS" and "FrameTime" in fields:
            header = fields
            break
    if header is None:
        sys.exit("no header line (first column EVENTS) found")

    ft_idx = header.index("FrameTime")
    width = len(header)
    warmup, frames, rejected = [], [], 0
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = split_record(line, width, ft_idx)
        if parts is None:
            rejected += 1
            continue
        rec = {}
        for k, name in enumerate(header):
            try:
                rec[name] = float(parts[k])
            except ValueError:
                rec[name] = None
        frame_time = rec["FrameTime"]
        if frame_time is None or frame_time <= 0:
            rejected += 1
            continue
        (warmup if len(warmup) < skip else frames).append(rec)
    return header, warmup, frames, rejected


def quantile(sorted_values, p):
    n = len(sorted_values)
    if n == 0:
        return 0.0
    idx = min(n - 1, max(0, int(round(p / 100.0 * (n - 1)))))
    return sorted_values[idx]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--skip", type=int, default=10,
                    help="frames treated as engine warm-up (excluded from stats)")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--report")
    args = ap.parse_args()

    header, warmup, recs, rejected = load(args.csv, args.skip)
    if not recs:
        sys.exit("no usable frame rows parsed")

    frames = [r["FrameTime"] for r in recs]
    ordered = sorted(frames)
    n = len(ordered)
    lines_out = []
    add = lines_out.append

    add(f"capture      : {args.csv}")
    add(f"usable frames: {n} (skipped warm-up {len(warmup)}, non-numeric rows {rejected})")
    add(f"mean={statistics.fmean(frames):.3f} ms  median={statistics.median(frames):.3f} ms"
        f"  fps_from_mean={1000.0 / statistics.fmean(frames):.2f}")
    add(f"p50={quantile(ordered, 50):.3f}  p90={quantile(ordered, 90):.3f}"
        f"  p95={quantile(ordered, 95):.3f}  p99={quantile(ordered, 99):.3f}"
        f"  p99.9={quantile(ordered, 99.9):.3f}  max={ordered[-1]:.3f}")
    if warmup:
        add("warm-up frames (excluded): " + ", ".join(f"{r['FrameTime']:.1f}" for r in warmup))
    add("")

    add("frame time histogram (ms):")
    buckets = [(0, 10), (10, 13.33), (13.33, 16.67), (16.67, 20), (20, 25),
               (25, 33.33), (33.33, 50), (50, 100), (100, 10 ** 9)]
    for lo, hi in buckets:
        count = sum(1 for f in frames if lo <= f < hi)
        label = f"[{lo:g},{hi:g})" if hi < 10 ** 9 else f"[{lo:g},inf)"
        add(f"  {label:>15} : {count:5d}  ({100.0 * count / n:5.2f}%)")
    add("")

    # recurring columns = columns present in (nearly) every frame record
    counts = {}
    for r in recs:
        for name, value in r.items():
            if value is not None:
                counts[name] = counts.get(name, 0) + 1
    recurring = {name for name, c in counts.items() if c >= 0.9 * n}
    trace_only = sorted(name for name in counts if name not in recurring)
    if trace_only:
        add(f"columns seen only in some frames (trace/region rows, not steady stats): {len(trace_only)}")

    columns = [c for c in header
               if c in recurring and c != "FrameTime"
               and (c.endswith("Time") or c.startswith("GPU/") or c.startswith("PSO/")
                    or c.startswith("FileIO/") or "Hitch" in c or c.startswith("Animation"))]

    ranked = sorted(recs, key=lambda r: r["FrameTime"], reverse=True)
    add("")
    add(f"worst {args.top} frames (contributors > 0.3 ms, largest first):")
    for rank, r in enumerate(ranked[: args.top], 1):
        pairs = [(c, r[c]) for c in columns if isinstance(r.get(c), float) and r[c] > 0.3]
        pairs.sort(key=lambda kv: kv[1], reverse=True)
        add(f"  #{rank:2d} FrameTime={r['FrameTime']:.2f} ms")
        for c, v in pairs[:12]:
            add(f"        {c:<50} {v:9.3f}")

    add("")
    add("column mean / p99 / max over usable frames (ms), sorted by max:")
    stats = []
    for c in columns:
        vals = [r[c] for r in recs if isinstance(r.get(c), float)]
        if not vals:
            continue
        vals.sort()
        stats.append((c, statistics.fmean(vals), quantile(vals, 99), vals[-1]))
    for c, mean, p99, mx in sorted(stats, key=lambda s: s[3], reverse=True):
        add(f"  {c:<50} mean={mean:9.3f}  p99={p99:9.3f}  max={mx:10.3f}")

    text = "\n".join(lines_out)
    print(text)
    if args.report:
        Path(args.report).write_text(text, encoding="utf-8")
        print(f"\n[written] {args.report}")


if __name__ == "__main__":
    main()