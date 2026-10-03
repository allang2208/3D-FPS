"""Timeline of trace events (FlushAsyncLoading, GC, Cmd, Region) inside a capture.

Usage:
  python trace_timeline.py <capture.csv> [--event FlushAsyncLoading] [--gap 0.25]

The capture records carry CSV_SCOPED_EVENT / region trace text with absolute
timestamps ("name##<seconds>"). Prints the events plus the gaps between them, so
a stall can be attributed to a wall-clock window.
"""

import argparse
import re
import sys
from pathlib import Path

# event text is glued to the first CSV field of a record; capture the name and
# its timestamp before the next "##" or the terminating comma of the field.
EVENT = re.compile(r"(?:^|;)([^;,#]+)##([0-9]+(?:\.[0-9]+)?)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--event", default=None, help="only this event name")
    ap.add_argument("--gap", type=float, default=0.2,
                    help="report gaps between consecutive events above this many seconds")
    ap.add_argument("--limit", type=int, default=400)
    args = ap.parse_args()

    text = Path(args.csv).read_text(encoding="utf-8", errors="replace")
    events = []
    for line in text.split("\n"):
        if not line:
            continue
        head = line.split(",", 1)[0]
        for name, ts in EVENT.findall(head):
            events.append((float(ts), name.strip()))
    events.sort()

    if args.event:
        selected = [e for e in events if e[1] == args.event]
        print(f"total events: {len(events)}, '{args.event}': {len(selected)}")
        if selected:
            print(f"time span of '{args.event}': {selected[0][0]:.3f} .. {selected[-1][0]:.3f} s")
            # bucket by second
            buckets = {}
            for ts, _ in selected:
                buckets[int(ts)] = buckets.get(int(ts), 0) + 1
            for second in sorted(buckets):
                print(f"  t={second:>4}s : {buckets[second]:5d}")
        events = selected

    print(f"\nevents ({len(events)}), showing gaps > {args.gap}s:")
    previous = None
    printed = 0
    for ts, name in events:
        if previous is not None:
            delta = ts - previous[0]
            if delta > args.gap and printed < args.limit:
                print(f"  {delta:8.3f}s gap  {previous[0]:10.3f} ({previous[1]}) -> {ts:10.3f} ({name})")
                printed += 1
        previous = (ts, name)
    print(f"\nfirst 20 events:")
    for ts, name in events[:20]:
        print(f"  {ts:10.3f}  {name}")
    print(f"\nlast 5 events:")
    for ts, name in events[-5:]:
        print(f"  {ts:10.3f}  {name}")


if __name__ == "__main__":
    main()