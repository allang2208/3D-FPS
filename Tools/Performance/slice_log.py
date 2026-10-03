"""Slice an Unreal log by timestamp window and surface load/hitch-related lines.

Usage:
  python slice_log.py <log> --from 18:18:49 --to 18:19:09 [--pattern extra]

Timestamps in UE logs look like [2026.09.21-10.18.49:123][ 42] (UTC by default in
these captures), so the match is done on the HH.MM.SS portion.
"""

import argparse
import re
import sys
from pathlib import Path

TS = re.compile(r"^\[(\d{4})\.(\d{2})\.(\d{2})-(\d{2})\.(\d{2})\.(\d{2}):(\d{3})\]")

INTERESTING = re.compile(
    r"FlushAsyncLoading|synchronously|Took [\d.]+ seconds|LogStreaming|LogLoad|"
    r"LogWorld: Bringing|SeamlessTravel|AsyncLoading|LogNavigation|"
    r"LogTemp: Warning: .*(?:hitch|slow|perf)|Slow task|FStreamable|"
    r"LogTexture|LogRenderer|PSO|Creating texture|LoadMap|shader",
    re.IGNORECASE,
)


def parse_ts(line):
    m = TS.match(line)
    if not m:
        return None
    _, _, _, hh, mm, ss, ms = m.groups()
    return int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms) / 1000.0


def to_seconds(text):
    hh, mm, ss = (text.split(":") + ["0"])[:3]
    return int(hh) * 3600 + int(mm) * 60 + int(ss)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--from", dest="start", required=True, help="HH:MM:SS")
    ap.add_argument("--to", dest="end", required=True, help="HH:MM:SS")
    ap.add_argument("--all", action="store_true", help="print every line in the window")
    ap.add_argument("--limit", type=int, default=400)
    args = ap.parse_args()

    start, end = to_seconds(args.start), to_seconds(args.end)
    printed = 0
    total = 0
    for line in Path(args.log).read_text(encoding="utf-8", errors="replace").splitlines():
        ts = parse_ts(line)
        if ts is None or not (start <= ts <= end):
            continue
        total += 1
        if args.all or INTERESTING.search(line):
            if printed < args.limit:
                print(line)
                printed += 1
    print(f"\n[{args.log}] lines in window: {total}, printed: {printed}", file=sys.stderr)


if __name__ == "__main__":
    main()