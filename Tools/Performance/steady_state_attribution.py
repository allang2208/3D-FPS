"""Compare a gate window against its steady-state surroundings.

CsvProfiler captures keep their first frames dominated by engine start-up and
asset warm-up. Those frames are not what the player experiences, so this tool
splits the capture at a gate frame and reports, for every column, the steady-state
median and the value on each remaining stall. It answers "what keeps stalling
after the game is running" rather than "what stalled once at start-up".

Usage:
  python steady_state_attribution.py <csv> [--gate 100] [--threshold 25]
                                     [--top 14] [--period]
"""

import argparse
import statistics
import sys
from pathlib import Path

# Columns that are cumulative counters or frame-rate constants and would swamp
# the ranking without saying anything about the stall.
IGNORED_PREFIXES = (
    "Shaders/NumShaders",
    "SystemMaxMB",
    "VirtualUsedMB",
    "PhysicalUsedMB",
    "MemoryFreeMB",
    "GPUMem/SystemBudgetMB",
    "GPUMem/LocalBudgetMB",
    "TextureStreaming/NonStreamingMips",
    "MaxFrameTime",
)


def load_rows(path):
    text = Path(path).read_text(encoding="utf-8", errors="replace").split("\n")
    header = text[0].split(",")
    width = len(header)
    ft = header.index("FrameTime")
    rows = []
    for line in text[1:]:
        if not line.strip():
            continue
        parts = line.split(",")
        if len(parts) < width:
            continue
        try:
            value = float(parts[ft])
        except ValueError:
            continue
        if value <= 0:
            continue
        rows.append((value, parts))
    return header, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--gate", type=int, default=100,
                    help="first steady-state frame index (default 100)")
    ap.add_argument("--threshold", type=float, default=25.0,
                    help="a frame is a stall above this many ms (default 25)")
    ap.add_argument("--top", type=int, default=14)
    ap.add_argument("--period", action="store_true",
                    help="print stall frame indices and the spacing between them")
    args = ap.parse_args()

    header, rows = load_rows(args.csv)
    steady = rows[args.gate:]
    if len(steady) < 20:
        print(f"not enough frames after gate {args.gate}", file=sys.stderr)
        return 1

    stalls = [(index, value, parts) for index, (value, parts) in
              enumerate(steady, start=args.gate) if value > args.threshold]
    normal = [(value, parts) for value, parts in steady if value <= args.threshold]

    print(f"capture       : {args.csv}")
    print(f"steady frames : {len(steady)} (gate {args.gate})")
    print(f"steady median : {statistics.median(v for v, _ in steady):.3f} ms")
    print(f"stalls        : {len(stalls)} above {args.threshold} ms")
    if not stalls:
        return 0

    if args.period:
        indices = [index for index, _, _ in stalls]
        gaps = [b - a for a, b in zip(indices, indices[1:])]
        print(f"stall frames  : {indices}")
        if gaps:
            print(f"spacing       : {gaps}")
            print(f"spacing median: {statistics.median(gaps):.0f} frames")

    # Rank by how much the column separates stalls from normal frames. A column
    # that is flat in normal frames and high in stalls is a cause candidate; one
    # that is merely large in both is just background cost.
    scored = []
    for index, name in enumerate(header):
        if name.startswith(IGNORED_PREFIXES):
            continue
        normal_values = []
        for _, parts in normal:
            try:
                normal_values.append(float(parts[index]))
            except (ValueError, IndexError):
                pass
        if len(normal_values) < 10:
            continue
        base = statistics.median(normal_values)
        spike = max(normal_values)
        stall_values = []
        for _, _, parts in stalls:
            try:
                stall_values.append(float(parts[index]))
            except (ValueError, IndexError):
                pass
        if len(stall_values) < len(stalls):
            continue
        peak = max(stall_values)
        # Relative lift over the normal peak, in ms; keeps units comparable.
        lift = peak - spike
        if lift <= 0:
            continue
        scored.append((lift, name, base, spike, peak))

    scored.sort(reverse=True)
    print()
    print(f"{'column':<52}{'normal_med':>11}{'normal_max':>11}{'stall_max':>11}")
    for lift, name, base, spike, peak in scored[:args.top]:
        print(f"{name:<52}{base:>11.4f}{spike:>11.4f}{peak:>11.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())