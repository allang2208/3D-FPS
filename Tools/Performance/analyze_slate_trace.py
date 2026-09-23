"""Summarize Insights event CSVs without mixing GPU and CPU timer statistics."""
import argparse
import bisect
import csv
import json
import math
from collections import defaultdict
from pathlib import Path


def distribution(values):
    ordered = sorted(values)
    if not ordered:
        return {"count": 0}
    def percentile(p):
        index = (len(ordered) - 1) * p
        lo, hi = math.floor(index), math.ceil(index)
        return ordered[lo] + (ordered[hi] - ordered[lo]) * (index - lo)
    return {"count": len(ordered), "mean_ms": sum(ordered) / len(ordered),
            "p50_ms": percentile(.5), "p95_ms": percentile(.95),
            "p99_ms": percentile(.99), "max_ms": ordered[-1]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--start", type=float, required=True)
    parser.add_argument("--end", type=float, required=True)
    args = parser.parse_args()
    directory = args.directory
    with (directory / "timers.csv").open(encoding="utf-8-sig") as source:
        timers = {int(row["Id"]): row for row in csv.DictReader(source)}
    def read_events(filename):
        with (directory / filename).open(encoding="utf-8-sig") as source:
            for row in csv.DictReader(source):
                start, end = float(row["StartTime"]), float(row["EndTime"])
                if math.isfinite(end) and args.start <= start <= end <= args.end:
                    yield (start, end, int(row["Depth"]), int(row["TimerId"]))
    events = list(read_events("game-events.csv"))
    frames = [[start, end, 0.] for start, end, _, timer in events
              if timers[timer]["Name"] == "FEngineLoop::Tick"]
    starts = [frame[0] for frame in frames]
    totals = defaultdict(lambda: {"count": 0, "inclusive_ms": 0., "exclusive_ms": 0.})
    stack = []
    hud_times = []
    for start, end, depth, timer in events:
        name = timers[timer]["Name"]
        while stack and stack[-1][0] >= depth:
            stack.pop()
        duration = (end - start) * 1000
        totals[name]["count"] += 1
        totals[name]["inclusive_ms"] += duration
        totals[name]["exclusive_ms"] += duration
        if stack and stack[-1][0] == depth - 1:
            totals[stack[-1][1]]["exclusive_ms"] -= duration
        stack.append((depth, name))
        if name.startswith("ColdSteelHUDWidget ") and name.endswith("_Tick"):
            hud_times.append(duration)
            index = bisect.bisect_right(starts, start) - 1
            if index >= 0 and end <= frames[index][1]:
                frames[index][2] += duration
    frame_ms = [(end - start) * 1000 for start, end, _ in frames]
    result = {"interval_trace_seconds": [args.start, args.end],
              "boundary_policy": "Complete scopes only; excludes pre-capture tail and unfinished scopes",
              "frame": distribution(frame_ms), "hud_tick": distribution(hud_times),
              "fps_from_mean_frame": 1000 / (sum(frame_ms) / len(frame_ms)),
              "hud_fraction_of_interval": sum(hud_times) / ((args.end - args.start) * 1000),
              "top_cpu_exclusive": sorted([{"name": name, **value} for name, value in totals.items()],
                                          key=lambda entry: entry["exclusive_ms"], reverse=True)[:25]}
    for label, slow in (("slow", True), ("fast", False)):
        selected = [frame for frame in frames if ((frame[1] - frame[0]) * 1000 >= 33.34) == slow]
        result[label] = {"frame": distribution([(end - start) * 1000 for start, end, _ in selected]),
                         "hud_tick": distribution([duration for _, _, duration in selected])}
    if (directory / "gpu-events.csv").exists():
        gpu = list(read_events("gpu-events.csv"))
        result["gpu_frame_scopes"] = distribution([(end - start) * 1000 for start, end, _, timer in gpu
                                                   if timers[timer]["Name"] == "Frame"])
        result["gpu_note"] = "GPU timestamp scope duration; includes queue gaps and is not hardware busy time"
    (directory / "analysis.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    with (directory / "frame-hud.csv").open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(["start_seconds", "frame_ms", "hud_tick_ms"])
        writer.writerows((start, (end - start) * 1000, hud) for start, end, hud in frames)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
