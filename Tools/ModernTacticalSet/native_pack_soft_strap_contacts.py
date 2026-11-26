"""Summarize the fixed strap and buckle surfaces intersecting each garment material."""
from pathlib import Path
import json
import os
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
R=ROOT/"SourceAssets/BackpackFit20261024/ModernTacticalNativePacks20261118"
sys.path.insert(0,str(Path(__file__).parent))
from helmet_nape_review import torso
from nape_backpack_author import tree, shells, contacts


def read(p):
    return json.loads(p.read_bytes())


def main():
    report={};contact_poses={}
    seated=os.environ.get("TS01_SEATED_STRAPS")=="1"
    refined={a["asset"]:a["positions"] for a in read(R/"Contact/author.json")["rows"]} if seated else {}
    for rig in ("Jason","Kaitlin"):
        helmets=shells(rig) if seated else {}
        g=torso(rig);gp=np.asarray(g["positions"]);gf=np.asarray(g["triangles"])
        garment=tree(gp,gf);materials=np.asarray(g["triangle_materials"])
        for family in ("Soft","Rigid"):
            author=read(R/family/"author.json")["rows"]
            sources=read(R/family/("sources.json" if family=="Soft" else "original-sources.json"))
            for a,q in zip(author,sources):
                if q["rig"]!=rig:continue
                item=q["item"]
                p=np.fromfile(refined.get(a["asset"],a["positions"]),"<f4").reshape(-1,3)
                cap=Path(q.get("source_directory") or q["source_harness_directory"])
                f=np.fromfile(cap/"triangles.bin","<i4").reshape(-1,3)
                if family=="Soft":
                    cargo=np.fromfile(q["cargo_vertices"],"u1")
                    f=f[~cargo[f].any(1)]
                if seated:
                    contact_poses[rig+"/"+item]=contacts([(p,f)],helmets)
                pairs=np.array(tree(p,f).overlap(garment),dtype=int)
                groups={}
                if seated:
                    ids=np.unique(f[pairs[:,0]]) if len(pairs) else np.array([],dtype=int)
                    weights=np.fromfile(cap/"mask.bin","<f4")
                    np.savez(R/"Contact"/(a["asset"].rsplit("/",1)[-1]+"-contacts.npz"),ids=ids,weights=weights[ids],points=p[ids])
                if len(pairs):
                    for material in sorted(set(materials[pairs[:,1]])):
                        sub=pairs[materials[pairs[:,1]]==material]
                        sample=p[f[np.unique(sub[:,0])]].mean(1)
                        groups[g["material_slots"][material]]=dict(
                            triangle_pairs=len(sub),strap_faces=len(np.unique(sub[:,0])),
                            region_min_cm=sample.min(0).tolist(),region_max_cm=sample.max(0).tolist())
                report[rig+"/"+item]=groups
    if seated:(R/"Contact/helmet-strap-contacts.json").write_text(json.dumps(contact_poses,indent=2))
    (R/("Contact/strap-contacts.json" if seated else "strap-contacts.json")).write_text(json.dumps(report,indent=2))
    for pair,groups in report.items():print(pair,{name:stats["triangle_pairs"] for name,stats in groups.items()},flush=True)
main()
