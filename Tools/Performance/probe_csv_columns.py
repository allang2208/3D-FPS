"""Probe how a CsvProfiler capture file actually lays out its records.

Usage: python probe_csv_columns.py <capture.csv> [rows]

Prints, for a few records, the wide row prefix and what the candidate alignment
rules produce at the FrameTime index, so the parser can be written against the
file's real shape instead of a guess.
"""

import sys
from pathlib import Path

path = Path(sys.argv[1])
rows = [int(a) for a in sys.argv[2:]] or [2, 3, 700, 900]

lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
header = None
for line in lines[:5]:
    fields = line.split(",")
    if "FrameTime" in fields:
        header = fields
        break
if header is None:
    sys.exit("no header")
ft = header.index("FrameTime")
width = len(header)
print(f"header: {width} columns, FrameTime at {ft}")
print(f"header name at {ft - 1}: {header[ft - 1]!r}, at {ft}: {header[ft]!r}, at {ft + 1}: {header[ft + 1]!r}")
print()

for r in rows:
    if r >= len(lines):
        continue
    line = lines[r]
    parts = line.split(",")
    print(f"--- row {r}: {len(parts)} comma fields, {len(line)} chars")
    print(f"    head: {line[:90]!r}")
    print(f"    tail: {line[-90:]!r}")
    for label, candidate in (
        ("plain[ft]", parts[ft] if len(parts) > ft else None),
        ("plain[-w+ft]", parts[len(parts) - width + ft] if len(parts) >= width else None),
    ):
        print(f"    {label:<12} = {candidate!r}")
    # locate the first field that parses as a small positive float and looks like
    # a frame time (1..100 ms) after the trace prefix
    for i, value in enumerate(parts):
        try:
            v = float(value)
        except ValueError:
            continue
        if 1.0 <= v <= 100.0:
            print(f"    first plausible frame-time-like field at index {i}: {v} "
                  f"(header would be {header[i] if i < width else 'past-end'!r})")
            break
    print()