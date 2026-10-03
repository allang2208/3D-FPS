"""Split total frame time into its thread budgets and report the steady-state mix.

A sustained frame-rate drop and a periodic hitch look identical if you only read
FrameTime. This shows where the budget goes once the scene has settled, so "the game
runs slower now" can be attributed to game thread, render thread or GPU.

The file is read as raw lines rather than through the csv module: CsvProfiler writes
a metadata row holding a single ~1 MB field, which exceeds csv's field limit and is
also why the header must be located by its EVENTS marker instead of by position.

Usage:
  python frame_budget.py --csv Saved/Res1440BodyOn20260922/baseline.csv --gate 420
"""

import argparse
import statistics as stats
from pathlib import Path

# Logical name -> CsvProfiler column.
WANTED = {
    "frame": "FrameTime",
    "game": "GameThreadTime",
    "render": "RenderThreadTime",
    "gpu": "GPUTime",
    "critical": "GameThreadTime_CriticalPath",
}


def load(path: Path):
    """Returns (rows, index) where rows are {logical_name: float}."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        raise SystemExit(f"empty capture: {path}")

    # The real header is the line whose first field is EVENTS.
    header_at = None
    for position, line in enumerate(lines):
        if line.split(",", 1)[0].strip() == "EVENTS":
            header_at = position
            break
    if header_at is None:
        raise SystemExit(f"no EVENTS header found in {path}")

    header = lines[header_at].split(",")
    index = {}
    for logical, column in WANTED.items():
        if column in header:
            index[logical] = header.index(column)
    missing = set(WANTED) - set(index)
    if missing:
        print(f"warning: columns absent from capture: {sorted(missing)}")

    width = len(header)
    rows = []
    for line in lines[header_at + 1:]:
        parts = line.split(",")
        if len(parts) < width:
            continue
        try:
            rows.append({k: float(parts[i]) for k, i in index.items()})
        except ValueError:
            continue
    return rows, index


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--gate", type=int, default=420,
                    help="frames to skip; start-up and streaming dominate before it")
    args = ap.parse_args()

    rows, index = load(Path(args.csv))
    if not rows:
        raise SystemExit("no numeric rows parsed")

    window = rows[args.gate:]
    print(f"rows parsed : {len(rows)}")
    print(f"window      : frames {args.gate}..{len(rows)} ({len(window)} frames)")

    print(f"\n{'channel':<10} {'median':>9} {'p90':>9} {'max':>10}")
    for logical in WANTED:
        if logical not in index:
            continue
        values = [r[logical] for r in window]
        p90 = sorted(values)[int(len(values) * 0.9)]
        print(f"{logical:<10} {stats.median(values):9.2f} {p90:9.2f} {max(values):10.2f}")

    median_frame = stats.median([r["frame"] for r in window])
    print(f"\nmedian frame : {median_frame:.2f} ms  ({1000.0 / median_frame:.1f} FPS)")

    # Throughput is what "the game feels slower" actually tracks.
    for budget, label in ((16.7, "60 FPS"), (33.3, "30 FPS")):
        over = sum(1 for r in window if r["frame"] > budget)
        print(f"frames over {budget:5.1f} ms ({label:>6}): {over:4d} "
              f"({100.0 * over / len(window):5.1f}%)")


if __name__ == "__main__":
    main()