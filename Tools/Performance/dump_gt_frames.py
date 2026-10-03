"""Dump only the game-thread / render-thread columns of the worst frames.

Usage: python dump_gt_frames.py <capture.csv> [--threshold 25] [--count 12]

A narrower view than dump_hitch_frames.py: it lists Exclusive/GameThread/*,
Exclusive/AllWorkers/*, SceneCulling/* and InitRenderResource style columns, so
the owning system of a hitch is readable without scrolling past memory counters.
"""

import argparse
import sys
from pathlib import Path

KEEP = (
    "Exclusive/GameThread/",
    "Exclusive/AllWorkers/",
    "Exclusive/RenderThread/",
    "SceneCulling/",
    "AnimationParallelEvaluation/",
    "NavigationBuild",
    "GC/",
    "LevelStreamingProfiling/",
    "PSO/",
    "StreamableManager/",
    "FileIO/",
    "InitRenderResource",
    "Shaders/Num",
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
    ap.add_argument("--count", type=int, default=12)
    ap.add_argument("--floor", type=float, default=0.05,
                    help="hide columns below this value")
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
            ft = float(parts[ft_idx])
        except ValueError:
            continue
        if ft <= 0:
            continue
        rows.append(parts)
    rows = rows[args.skip:]
    ranked = [r for r in rows if float(r[ft_idx]) > args.threshold]
    ranked = sorted(ranked, key=lambda r: float(r[ft_idx]), reverse=True)[: args.count]

    out = []
    add = out.append
    add(f"capture: {args.csv}")
    add(f"frames : {len(rows)}; showing {len(ranked)} frames above {args.threshold} ms")
    add("")
    for i, row in enumerate(ranked, 1):
        add(f"=== frame #{i}  FrameTime={float(row[ft_idx]):.1f} ms  "
            f"GT={row[header.index('GameThreadTime')]}  "
            f"RT={row[header.index('RenderThreadTime')]}  "
            f"GPU={row[header.index('GPUTime')]} ===")
        items = []
        for k, name in enumerate(header):
            if not any(name.startswith(p) or p in name for p in KEEP):
                continue
            try:
                value = float(row[k])
            except ValueError:
                continue
            if value > args.floor:
                items.append((name, value))
        items.sort(key=lambda kv: kv[1], reverse=True)
        for name, value in items[:40]:
            add(f"    {name:<60}{value:12.3f}")
        add("")

    text = "\n".join(out)
    print(text)
    if args.report:
        Path(args.report).write_text(text, encoding="utf-8")
        print(f"[written] {args.report}")


if __name__ == "__main__":
    main()