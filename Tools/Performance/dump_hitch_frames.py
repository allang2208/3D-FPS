"""Dump every non-zero stat of the worst frames in a UE CsvProfiler capture.

Usage:
  python dump_hitch_frames.py <capture.csv> [--skip N] [--count N] [--report out.txt]

The CsvProfiler captures written by this project prefix trace events to each
record line, so records are aligned left after the trace prefix and validated on
FrameTime. Output is one block per hitch frame, listing every stat that is
non-zero, which makes the owning system visible without a debugger.
"""

import argparse
import re
import sys
from pathlib import Path

DROP = re.compile(
    r"^(Scheduler/|FMsgLogf|CsvProfiler/|RenderThreadIdle/|GPUScene|"
    r"RHI/|Audio/|Slate/|RealtimeGPU|RenderTargetPool)"
)


def read_header(lines):
    """The header line is the one whose first column is EVENTS."""
    for line in lines[:5]:
        fields = line.split(",")
        if fields[0] == "EVENTS" and "FrameTime" in fields:
            return fields
    sys.exit("no header line (first column EVENTS) found")


def split_record(line, width, ft_idx):
    """Return the CSV fields of one capture record, or None when unusable.

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


def load(csv_path):
    lines = Path(csv_path).read_text(encoding="utf-8", errors="replace").split("\n")
    header = read_header(lines)
    width = len(header)
    ft_idx = header.index("FrameTime")
    records = []
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = split_record(line, width, ft_idx)
        if parts is None:
            continue
        row = {}
        for k, name in enumerate(header):
            try:
                row[name] = float(parts[k])
            except ValueError:
                pass
        row["FrameTime"] = float(parts[ft_idx])
        if row["FrameTime"] <= 0:
            continue
        records.append(row)
    return header, records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--skip", type=int, default=10)
    ap.add_argument("--count", type=int, default=8)
    ap.add_argument("--threshold", type=float, default=None,
                    help="only dump frames above this FrameTime (ms)")
    ap.add_argument("--below", type=float, default=None,
                    help="only dump frames below this FrameTime (ms); use with --threshold to isolate a band")
    ap.add_argument("--gate", type=int, default=0,
                    help="ignore frames before this index, to skip start-up")
    ap.add_argument("--report")
    args = ap.parse_args()

    header, records = load(args.csv)
    warm, rest = records[: args.skip], records[args.skip:]
    if args.gate > args.skip:
        rest = records[args.gate:]
    ranked = sorted(rest, key=lambda r: r["FrameTime"], reverse=True)
    if args.threshold is not None:
        ranked = [r for r in ranked if r["FrameTime"] >= args.threshold]
    else:
        ranked = ranked[: args.count]
    if args.below is not None:
        ranked = [r for r in ranked if r["FrameTime"] <= args.below]

    out = []
    add = out.append
    add(f"capture: {args.csv}")
    add(f"frames : {len(rest)} (warm-up skipped {len(warm)})")
    add(f"dumping {len(ranked)} frame(s)")
    add("")
    for index, row in enumerate(ranked, 1):
        add(f"=== frame #{index}  FrameTime={row['FrameTime']:.2f} ms  "
            f"GameThread={row.get('GameThreadTime', float('nan')):.2f}  "
            f"RenderThread={row.get('RenderThreadTime', float('nan')):.2f}  "
            f"GPU={row.get('GPUTime', float('nan')):.2f} ===")
        items = [(k, v) for k, v in row.items()
                 if k != "FrameTime" and isinstance(v, float) and v > 0.0005
                 and not DROP.match(k)]
        items.sort(key=lambda kv: kv[1], reverse=True)
        for k, v in items:
            add(f"      {k:<58} {v:12.4f}")

    text = "\n".join(out)
    print(text)
    if args.report:
        Path(args.report).write_text(text, encoding="utf-8")
        print(f"\n[written] {args.report}")


if __name__ == "__main__":
    main()