"""Verify the unchanged rigid cargo, final anchor geometry and mounted shell on both bodies."""
import json
from pathlib import Path
import sys

import numpy as np
from mathutils import Quaternion

P=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from helmet_nape_review import torso
from nape_backpack_author import shells,contacts,tree

R=P/"SourceAssets/BackpackFit20261024/ModernTacticalNativePacks20261118/Rigid"


def read(file):
    return json.loads(file.read_bytes())


def main():
    stage=read(R/"staged.json")
    routes=read(R/"routes.json")
    sources=read(R/"original-sources.json")
    output={}
    problems={}
    for rig in ("Jason","Kaitlin"):
        helmets=shells(rig)
        clothing=torso(rig)
        shirt=tree(np.asarray(clothing["positions"]),np.asarray(clothing["triangles"]))
        for source,route,sk,sm in zip(sources,routes,stage["rows"],stage["statics"]):
            if route["rig"]!=rig:continue
            skp=np.fromfile(sk["positions"],dtype="<f4").reshape(-1,3)
            skf=np.fromfile(Path(source["source_harness_directory"])/"triangles.bin",dtype="<i4").reshape(-1,3)
            smp=np.fromfile(sm["positions"],dtype="<f4").reshape(-1,3)
            smf=np.fromfile(Path(source["source_shell_directory"])/"triangles.bin",dtype="<i4").reshape(-1,3)
            x,y,z,w=route["rigid_rotation_quat"]
            rot=np.array(Quaternion((w,x,y,z)).to_matrix())
            world=smp@rot.T+route["rigid_location"]
            measures=contacts([(skp,skf),(world,smf)],helmets)
            cloth_hits=len(tree(world,smf).overlap(shirt))
            name=rig+"/"+route["item"]
            output[name]=dict(helmet_poses=measures,rigid_cargo_intersecting_upper_triangles=cloth_hits)
            if any(measures.values()) or cloth_hits:
                # Preserve bag shape and its original native height; determine
                # any additional fore/aft movement from real triangle contacts.
                for shift in np.arange(.25,5.01,.25):
                    body=world-[0,shift,0];surf=tree(body,smf)
                    if not surf.overlap(shirt) and not any(surf.overlap(helm) for helm,_ in helmets.values()):
                        problems[name]=float(shift+.20)
                        break
                if name not in problems:raise RuntimeError(f"No clean rigid placement for {name}")
            print(name,"shapes",measures,"garment",cloth_hits,flush=True)
    evidence=R/"geometric-contact.json"
    evidence.write_text(json.dumps(output,indent=2))
    if problems:
        offsets=R/"helmet-adjustments.json"
        prev=read(offsets) if offsets.exists() else {}
        prev.update({k:prev.get(k,0.)+v for k,v in problems.items()})
        offsets.write_text(json.dumps(prev,indent=2))
        raise RuntimeError(f"Rebuild the six fitted harnesses at the measured placements: {problems}")
    (R/"author.json").write_text(json.dumps(stage,indent=2),encoding="utf-8")
    print("ORIGINAL_CARGO_SHAPES_READY",len(routes),flush=True)


if __name__=="__main__":
    main()
