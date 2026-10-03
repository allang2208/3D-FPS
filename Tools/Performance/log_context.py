"""Print an Unreal log window around the first occurrence of a pattern.

Usage: python log_context.py <log> <pattern> [--before 5] [--after 25] [--max 3]
"""

import argparse
import re
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("pattern")
    ap.add_argument("--before", type=int, default=5)
    ap.add_argument("--after", type=int, default=25)
    ap.add_argument("--max", type=int, default=3)
    args = ap.parse_args()

    lines = Path(args.log).read_text(encoding="utf-8", errors="replace").splitlines()
    regex = re.compile(args.pattern)
    shown = 0
    for index, line in enumerate(lines):
        if not regex.search(line):
            continue
        shown += 1
        start = max(0, index - args.before)
        end = min(len(lines), index + args.after + 1)
        print(f"----- match {shown} at line {index + 1} -----")
        for i in range(start, end):
            marker = ">>" if i == index else "  "
            text = lines[i]
            print(f"{marker} {i + 1:6d} {text[:200]}")
        if shown >= args.max:
            break
    if shown == 0:
        print(f"no match for {args.pattern!r}", file=sys.stderr)


if __name__ == "__main__":
    main()