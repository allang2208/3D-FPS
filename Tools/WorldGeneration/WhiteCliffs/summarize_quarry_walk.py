"""Publish the measured walk frames and pair the unaltered player-view screenshots."""
import csv
import json
import math
import shutil
import sys
from statistics import median
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

run, out = map(Path, sys.argv[1:])
ev = run / "Evidence"
if "complete=1" not in (ev / "walk.txt").read_text(encoding="utf-8-sig"):
    raise SystemExit("The quarry walk did not finish")
out.mkdir(parents=True, exist_ok=True)

def rows(name):
    with (ev / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

frames = rows("frames.csv")
poses = rows("poses.csv")
stats = {}
for lap, label in (("0", "clear"), ("1", "post_rain")):
    groups = defaultdict(list)
    for row in frames:
        if row["lap"] == lap:
            groups["all"].append(row)
            if row["leg"]!="upper":
                groups["entrance_to_toe"].append(row)
            groups[row["leg"]].append(row)
    stats[label] = {}
    for group, records in groups.items():
        ms = sorted(float(r["frame_ms"]) for r in records)
        spikes = [r for r in records if float(r["frame_ms"])>50.]
        stats[label][group] = dict(frames=len(ms), duration_s=round(sum(ms)/1000,2),
                                  p95_ms=ms[math.ceil(.95*len(ms))-1],
                                  over_50_ms=len(spikes), max_ms=ms[-1],
                                  spike_median_ms={k:round(median(float(r[k]) for r in spikes),2)
                                                   for k in ("game_ms","render_ms","gpu_ms")} if spikes else {},
                                  wetness_range=[min(float(r["wetness"]) for r in records),
                                                 max(float(r["wetness"]) for r in records)],
                                  rain_max=max(float(r["rain"]) for r in records))

labels = ["入口全景", "工棚与方坯", "吊装坪与绞盘", "主采面", "石脚与碎砾"]
sites = [r["site"] for r in poses if r["lap"]=="0"]
if "06_bend" in sites:
    labels += ["运输路内弯","上坡回望"]
if len(sites)!=len(labels) or len(poses)!=2*len(labels):
    raise SystemExit("Incomplete set of photo stations")
w,h = 720,405
sheet = Image.new("RGB",(w*2,54+(h+36)*len(sites)),(236,233,225))
draw = ImageDraw.Draw(sheet)
font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",22)
for i,title in enumerate(("晴天","雨后")):draw.text((14+w*i,11),title,font=font,fill="#2a332f")
deltas = {}
for i, (site, name) in enumerate(zip(sites,labels)):
    y = 54+i*(h+36)
    draw.text((14,y), name, font=font,fill="#2a332f")
    a,b = [next(r for r in poses if r["lap"]==lap and r["site"]==site) for lap in ("0","1")]
    deltas[site]=dict(eye_cm=round(math.dist([float(a[c]) for c in ("eye_x","eye_y","eye_z")],
                                             [float(b[c]) for c in ("eye_x","eye_y","eye_z")]),4),
                      rotation_deg=max(abs((float(a[c])-float(b[c])+180)%360-180) for c in ("pitch","yaw","roll")),
                      fov_deg=abs(float(a["fov"])-float(b["fov"])))
    for j,prefix in enumerate(("dry","wet")):
        filename=f"{prefix}_{site}.png"
        shutil.copy2(ev/filename,out/filename)
        with Image.open(ev/filename) as im:
            sheet.paste(im.convert("RGB").resize((w,h),Image.Resampling.LANCZOS),(j*w,y+36))
sheet.save(out/"comparison.jpg",quality=90)
for name in ("frames.csv","poses.csv","contacts.csv","walk.txt","world.txt"):
    shutil.copy2(ev/name,out/name)
for name in ("launch.json","exit.json"):
    if (run/name).exists():shutil.copy2(run/name,out/name)
contacts = rows("contacts.csv")
summary = {"p95_method":"nearest rank over moving frames", "strict_threshold_ms":50,
           "timing":stats, "paired_camera_deltas":deltas,
           "contact_count":len(contacts),
           "min_sample_gap_above_2cm":[r for r in contacts if float(r["min_sample_gap_cm"])>2]}
(out/"metrics.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding="utf8")
print(json.dumps({k:v["all"] for k,v in stats.items()},indent=2))
