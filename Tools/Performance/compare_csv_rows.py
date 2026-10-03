"""Compare CsvProfiler capture rows that have different field counts.

Usage: python compare_csv_rows.py <capture.csv> [which_row ...]

Prints the exact field layout of one 450-field record and one wider record, then
reports which schema columns the wider record appears to be missing, by locating
distinctive header values inside the row.
"""

import sys
from pathlib import Path

path = Path(sys.argv[1])
lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
header = None
for line in lines[:5]:
    fields = line.split(",")
    if fields[0] == "EVENTS" and "FrameTime" in fields:
        header = fields
        break
if header is None:
    sys.exit("no header")
width = len(header)
print(f"schema: {width} columns")

records = []
for index, line in enumerate(lines[1:], start=1):
    if not line.strip():
        continue
    parts = line.split(",")
    records.append((index, len(parts), parts))

from collections import Counter
counts = Counter(length for _, length, _ in records)
print("field-count histogram:", counts.most_common())

wide = next((r for r in records if r[1] == width), None)
narrow = next((r for r in records if r[1] > width), None)

for label, rec in (("aligned", wide), ("wider", narrow)):
    if rec is None:
        print(f"{label}: none")
        continue
    index, length, parts = rec
    print(f"\n=== {label} row {index}: {length} fields ===")
    print("  first 16:", parts[:16])
    print("  last 16 :", parts[-16:])
    # Where does each schema column land in this row?
    print("  index of 'FrameTime' value in row:", [
        i for i, v in enumerate(parts) if v.startswith("25023") or v.startswith("11.")][:6])
    # Find schema columns whose header text can't be matched positionally by
    # checking a few distinctive non-numeric values.
    hits = {}
    for i, v in enumerate(parts):
        if v in header:
            hits[v] = i
    print("  positions of header-text-like values:", hits)
    # Which schema columns hold a value that looks like it belongs elsewhere?
    for probe in ("FrameTime", "MaxFrameTime", "MemoryFreeMB", "GPUTime"):
        want = header.index(probe)
        print(f"  schema[{want}]={header[want]!r} value in row = "
              f"{parts[want] if want < length else 'past end'!r}")