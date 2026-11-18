"""Summarize the opt-in probe's actual end-frame intervals and network load logs."""
import argparse
import json
import math
import re
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("run", type=Path)
args = parser.parse_args()

def stats(samples):
    values = sorted(s["ms"] for s in samples)
    if not values:
        return {"frames": 0}
    return {"frames": len(values), "p50_ms": round(values[math.ceil(len(values)*.5)-1],3),
            "p95_ms": round(values[math.ceil(len(values)*.95)-1],3),
            "p99_ms": round(values[math.ceil(len(values)*.99)-1],3), "max_ms": round(values[-1],3),
            **{f"over_{t}ms": sum(v>t for v in values) for t in (50,100,200)}}

report = {}
for role in ("host", "client", "late"):
    path = args.run / "Evidence" / f"{role}-result.json"
    if not path.exists():
        continue
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    log = (args.run / f"{role}.log").read_text(encoding="utf-8-sig",errors="replace")
    serializations = [{"ms":float(m.group(1)),"object":m.group(2)} for m in re.finditer(
        r"Long net serialize:\s*([\d.]+)ms, Serialized Object ([^\r\n]+)",log)]
    phases = {p:stats([s for s in data["frames"] if s["phase"] == p]) for p in sorted({s["phase"] for s in data["frames"]})}
    arrivals = []
    for event in data["events"]:
        if event["name"].startswith(("monsters_", "actor_spawn_")):
            nearby = [s for s in data["frames"] if abs(s["frame"]-event["frame"])<=2]
            arrivals.append({**event,"nearby_frames":nearby})
    report[role] = {k:data.get(k) for k in ("passed","detail","ready_seconds","rendered","max_monsters","async_net_loading","lag_ms","loss_percent","seed","world_id")}
    report[role].update(phases=phases,arrivals=arrivals,events=data["events"],sync_loads=data["sync_loads"],long_net_serializes=serializations,
        net_errors=[line for line in log.splitlines() if any(x in line for x in ("Forced blocking load", "Failed to resolve path", "SupportsObject", "could not resolve the new relative movement base", "LogNet: Error", "LogNetPackageMap: Error"))])
    report[role]["spawn_frames"] = [
        {"name":e["name"], "frame":e["frame"], "phase":e["phase"],
         "reaction_defaults_loaded":e.get("reaction_defaults_loaded"),
         "ms":next((round(s["ms"],3) for s in e["nearby_frames"] if s["frame"]==e["frame"]),None)}
        for e in arrivals if e["name"].startswith("actor_spawn_")]
    def frame_ms(event):
        return next((round(s["ms"],3) for s in data["frames"] if s["frame"]==event["frame"]),None)
    report[role]["player_spawn_frames"] = [
        {**e,"ms":frame_ms(e)} for e in data["events"] if e["name"]=="player_spawn"]
    report[role]["gc_cycles"] = [
        {**e,"frame_ms":frame_ms(e)} for e in data["events"] if e["name"]=="gc_end"]
    ready=data.get("ready_seconds",-1)
    report[role]["entry_first_10s"] = stats([
        s for s in data["frames"] if ready>=0 and ready<=s["time"]<ready+10])
    report[role]["village_planting"] = [
        {"count":int(m.group(1)),"groups":int(m.group(2))}
        for m in re.finditer(r"VILLAGE_PLANTING_DISPLAY count=(\d+) groups=(\d+)",log)]
    exit_path = args.run / f"exit-{role}.json"
    report[role]["process_exit"] = json.loads(exit_path.read_text(encoding="utf-8-sig")) if exit_path.exists() else None
(args.run/"performance-summary.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({k:{field:v[field] for field in ("passed","ready_seconds","phases","long_net_serializes","net_errors")} for k,v in report.items()},indent=2))
