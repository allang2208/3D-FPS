"""Inspect the restored closed cargo surfaces on the fitted body and head poses."""
from pathlib import Path
import json
import sys
import numpy as np

P=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from helmet_nape_review import torso
from nape_backpack_author import shells,contacts,tree

R=P/"SourceAssets/BackpackFit20261024/ModernTacticalNativePacks20261118/Soft"


def read(name):return json.loads((R/name).read_bytes())


def main():
    staged=read("staged.json");sources=read("sources.json");report={};adjust={}
    for rig in ("Jason","Kaitlin"):
        helmets=shells(rig);g=torso(rig);shirt=tree(np.asarray(g["positions"]),np.asarray(g["triangles"]))
        for q,r in zip(sources,staged["rows"]):
            if q["rig"]!=rig:continue
            key=rig+"/"+q["item"]
            p=np.fromfile(r["positions"],"<f4").reshape(-1,3)
            f=np.fromfile(Path(q["source_directory"])/"triangles.bin","<i4").reshape(-1,3)
            cargo=np.fromfile(q["cargo_vertices"],"u1").astype(bool)
            cf=f[cargo[f].all(1)];cold=tree(p,cf);h=contacts([(p,f)],helmets)
            hits=len(cold.overlap(shirt))
            report[key]=dict(full_pack_vs_helmet=h,cargo_against_clothing=hits,
                             shoulder_strap_and_hardware_against_clothing=len(tree(p,f[~cargo[f].any(1)]).overlap(shirt)))
            if hits or any(h.values()):
                for shift in np.arange(.25,9,.25):
                    body=tree(p-[0,shift,0],cf)
                    if not body.overlap(shirt) and not any(body.overlap(t) for t,_ in helmets.values()):
                        adjust[key]=float(shift+.2);break
                if key not in adjust:raise RuntimeError("No native volume placement for "+key)
            print(key,hits,max(h.values()),flush=True)
    (R/"geometric-contact.json").write_text(json.dumps(report,indent=2))
    if adjust:
        current=read("adjustments.json") if (R/"adjustments.json").exists() else {}
        current.update({k:current.get(k,0.)+v for k,v in adjust.items()})
        (R/"adjustments.json").write_text(json.dumps(current,indent=2))
        raise RuntimeError("Rebuild soft pack seams at the measured clearance: "+str(adjust))
    (R/"author.json").write_text(json.dumps(staged,indent=2))


if __name__=="__main__":main()
