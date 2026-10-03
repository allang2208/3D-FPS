"""Rank the stats that separate hitch frames from normal frames in a capture.

Usage:
  python attribute_hitches.py <capture.csv> [--threshold 25] [--top 25] [--report out.txt]

For every column, compares the median across normal frames with the median and
max across hitch frames (FrameTime > threshold), and prints the columns whose
values move the most. This is what makes a hitch attributable to a subsystem
without a debugger: the subsystem that owns the frame shows a huge delta, while
steady-state systems do not.
"""

import argparse
import re
import statistics
import sys
from pathlib import Path

DROP = re.compile(
    r"^(Scheduler/|FMsgLogf|CsvProfiler/|RenderThreadIdle/|GPUScene|"
    r"BandwidthAllocator/|RHI/|Audio/|RealtimeGPU|RenderTargetPool|"
    r"NavigationBuildDetailed/)"
)

# counters that are not durations and would dominate a delta ranking
NOT_A_DURATION = re.compile(
    r"MB$|Kbps$|Count$|Percent$|^Ticks/|^DrawCall/|^ActorCount/|^View/|"
    r"NumShaders|NumTasks|^CPUUsage|^RDGCount|^GPUScene|QueueDepth|"
    r"^Shaders/|TEviction|Num$"
)


def read_header(lines):
    for line in lines[:5]:
        fields = line.split(",")
        if fields[0] == "EVENTS" and "FrameTime" in fields:
            return fields
    sys.exit("no header line (first column EVENTS) found")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--skip", type=int, default=10)
    ap.add_argument("--threshold", type=float, default=25.0)
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--report")
    args = ap.parse_args()

    lines = Path(args.csv).read_text(encoding="utf-8", errors="replace").split("\n")
    header = read_header(lines)
    width = len(header)
    ft_idx = header.index("FrameTime")

    rows = []
    for index, line in enumerate(lines[1:]):
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
        rows.append((len(rows), parts))
    rows = rows[args.skip:]

    normal = [(i, r) for i, r in rows if float(r[ft_idx]) <= args.threshold]
    hitch = [(i, r) for i, r in rows if float(r[ft_idx]) > args.threshold]
    if not normal or not hitch:
        sys.exit(f"need both normal and hitch frames (normal={len(normal)}, hitch={len(hitch)})")

    out = []
    add = out.append
    add(f"capture  : {args.csv}")
    add(f"frames   : {len(rows)}  normal<= {args.threshold}ms: {len(normal)}  hitch> {args.threshold}ms: {len(hitch)}")
    add(f"frame times of hitches: " + ", ".join(f"{float(r[ft_idx]):.1f}" for _, r in hitch))
    add("")

    ranked = []
    for k, name in enumerate(header):
        if DROP.match(name) or NOT_A_DURATION.search(name):
            continue
        nvals, hvals = [], []
        for _, r in normal:
            try:
                nvals.append(float(r[k]))
            except ValueError:
                pass
        for _, r in hitch:
            try:
                hvals.append(float(r[k]))
            except ValueError:
                pass
        if not nvals or not hvals:
            continue
        nmed = statistics.median(nvals)
        hmed = statistics.median(hvals)
        hmax = max(hvals)
        delta = hmed - nmed
        if delta <= 0.05 and hmax - nmed <= 0.5:
            continue
        ranked.append((delta, hmax - nmed, name, nmed, hmed, hmax))

    add(f"{'column':<56}{'normal_med':>12}{'hitch_med':>12}{'hitch_max':>12}{'delta':>12}")
    for delta, peak, name, nmed, hmed, hmax in sorted(ranked, key=lambda t: t[1], reverse=True)[: args.top]:
        add(f"{name:<56}{nmed:12.3f}{hmed:12.3f}{hmax:12.3f}{delta:12.3f}")

    text = "\n".join(out)
    print(text)
    if args.report:
        Path(args.report).write_text(text, encoding="utf-8")
        print(f"[written] {args.report}")


if __name__ == "__main__":
    main()