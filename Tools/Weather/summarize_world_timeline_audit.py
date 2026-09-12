"""Summarize live (non-fixture) weather/travel acceptance from its runtime log."""
from pathlib import Path
import argparse
import json
import re

parser = argparse.ArgumentParser()
parser.add_argument("--log", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
log = args.log.read_text(encoding="utf-8", errors="replace")
results = []
for row in re.finditer(r"WEATHER_WORLD_RESULT map=(\S+) route=(\d+) checks=(\d+) failures=(\d+) samples=(\d+) transitions=(\d+) states=(\d+)", log):
    results.append(dict(zip(["map", "route", "checks", "failures", "samples", "transitions", "states"],
                            [row[1], *map(int, row.groups()[1:])])) )
clocks = [dict(map=m[1], external=bool(int(m[2])), elapsed=float(m[3]), clock=float(m[4]))
          for m in re.finditer(r"WEATHER_WORLD_CLOCK map=(\S+) external=(\d+) elapsed=([\d.]+) clock=([\d.]+)", log)]
fatal = re.findall(r".*(?:Fatal error:|Assertion failed:|Ensure condition failed:).*", log)
failed = re.findall(r".*WEATHER_WORLD_CHECK FAIL.*", log)
summary = re.search(r"WEATHER_WORLD_AUDIT_(PASS|FAIL) checks=(\d+) failures=(\d+) worlds=(\d+) travels=(\d+)", log)
passed = bool(summary and summary[1] == "PASS" and len(results) == 4 and not failed and not fatal
              and all(row["failures"] == 0 for row in results))
report = dict(passed=passed, checks=int(summary[2]) if summary else 0, routes=results, clocks=clocks,
              failed_checks=failed, fatal_errors=fatal, renderer="D3D12" if 'rhiname="D3D12"' in log else "unknown",
              normal_day_seconds=2160, accelerated_day_seconds=60, seed=122,
              runtime_weather_states=["Clear", "Cloudy", "Rain", "Storm"],
              light_rain_validation="32-day schedule sample; not a separate rendered light-rain run",
              log=str(args.log), travel="DayNight -> Normandy -> Trench -> DayNight",
              UI="Live data; no EventTimelineUIAudit fixture; Alt, expand, details, filters, forecast arrival, midnight and rebuilt HUD")
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print(json.dumps(dict(passed=passed, checks=report["checks"], routes=len(results)), ensure_ascii=False))
raise SystemExit(0 if passed else 1)
