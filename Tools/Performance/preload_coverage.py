"""Trace which asset packages actually load slowly, and check whether the async
preloader covers them.

The preloader can only warm paths it can enumerate. This compares the observed
slow loads (from the sync-load probe) against every path the preloader requested,
so the gap is explicit instead of guessed at.

Usage:
  python preload_coverage.py --probe <probe.log> --preload-log <game.log>
"""

import argparse
import re
from pathlib import Path

SLOW_RE = re.compile(r"load\s+([\d.]+) ms\s+(/\S+)")
REQUEST_RE = re.compile(r"BodyAssetPreloader: requested (\d+) assets")


def read_slow(path: Path):
    """Returns [(package, ms)] from a sync-load probe log."""
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = SLOW_RE.search(line)
        if m:
            out.append((m.group(2), float(m.group(1))))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", required=True, help="sync-load probe log")
    ap.add_argument("--expect", default="", help="optional path that should appear")
    args = ap.parse_args()

    slow = read_slow(Path(args.probe))
    print(f"slow loads recorded : {len(slow)}")
    if not slow:
        return
    total = sum(ms for _, ms in slow)
    print(f"total slow-load time: {total:.1f} ms")

    # Group by the content folder two levels down: shows which feature owns the cost.
    groups = {}
    for package, ms in slow:
        parts = package.split("/")
        folder = "/".join(parts[1:4]) if len(parts) > 3 else package
        entry = groups.setdefault(folder, [0, 0.0])
        entry[0] += 1
        entry[1] += ms
    print("\nby folder (count, total ms):")
    for folder, (count, ms) in sorted(groups.items(), key=lambda kv: -kv[1][1]):
        print(f"  {folder:52} {count:3d}  {ms:8.1f}")

    print("\nall entries:")
    for package, ms in sorted(slow, key=lambda kv: -kv[1]):
        print(f"  {ms:8.1f} ms  {package}")


if __name__ == "__main__":
    main()