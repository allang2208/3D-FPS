"""Measure the final helmet against the fitted shirt and carrier in reference pose."""
import hashlib
import json
from pathlib import Path

import numpy as np
from mathutils.bvhtree import BVHTree

SET=Path(__file__).resolve().parents[2]/"SourceAssets/ModernTacticalSet20261113"
OUT=SET/"HelmetNapeR3/Authored"
read=lambda file:json.loads(file.read_bytes())
sources={row["asset"]:Path(row["file"]) for row in read(SET/"CombatShirtR4/authored.json")["rows"]}
summary={}
for rig,entry in read(SET/"SetReview20261118/body-fit.json").items():
    source=sources[entry["equipped"][0].split(".")[0]]
    shirt=read(source)
    p=np.array(shirt["positions"],dtype="<f4")
    delta={}
    for name in ("cloth","carrier"):
        patch=np.load(SET/"ShoulderFit20261118"/f"{rig}-{name}.npz")
        delta.update({a.tobytes():b for a,b in zip(patch["before"].astype("<f4"),patch["after"])})
    p=np.array([delta.get(v.tobytes(),v) for v in p])
    f=np.array(shirt["triangles"])
    slots=np.array(shirt["triangle_materials"])
    mats=shirt["material_slots"]
    cloth=f[np.array([not mats[s].startswith("NATIVE:") for s in slots])]
    garment=BVHTree.FromPolygons(p.tolist(),cloth.tolist(),all_triangles=True)
    helmet=read(OUT/f"helmet_{rig}_world.json")
    vertices=np.array(helmet["positions"])
    faces=np.array(helmet["triangles"])
    hi=BVHTree.FromPolygons(vertices.tolist(),faces.tolist(),all_triangles=True)
    posterior=vertices[(vertices[:,1]<0)&(vertices[:,2]<vertices[:,2].max()-12)]
    gap=min(garment.find_nearest(x.tolist())[3] for x in posterior)
    summary[rig]=dict(collar_intersections=len(hi.overlap(garment)),
                      posterior_helmet_samples=len(posterior),min_posterior_to_clothing_cm=round(float(gap),3),
                      source_sha256=hashlib.sha256((OUT/f"helmet_{rig}_world.json").read_bytes()).hexdigest(),
                      wear_sha256=hashlib.sha256((OUT/f"helmet_{rig}_wear.json").read_bytes()).hexdigest())
    print("NAPE_COLLAR",rig,summary[rig],flush=True)
(OUT/"nape-collar.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
