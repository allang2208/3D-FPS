"""Measure garment contact and the six physical ends of each affected TS01 harness."""
import json
from pathlib import Path
import sys

import numpy as np
from mathutils import Quaternion,Vector

sys.path.insert(0,str(Path(__file__).parent))
from helmet_nape_review import torso
from nape_backpack_author import tree


R=Path(__file__).resolve().parents[2]/"SourceAssets/BackpackFit20261024/ModernTacticalNativePacks20261118"
F=R/"ExfilR4"


def read(path):
    return json.loads(path.read_bytes())


def meshbuffers(folder,faces):
    return np.fromfile(folder/"positions.bin","<f4").reshape(-1,3),np.fromfile(folder/faces,"<i4").reshape(-1,3)


def main(saved):
    cases=read(F/"prior.json")
    seams=read(F/"seam-fit.json")
    routes={q["rig"]+"/"+q["item"]:q for q in read(R/"Rigid/routes.json")}
    levels=read(R/"lod-read.json") if saved else {}
    record={}
    for rig in ("Jason","Kaitlin"):
        garment=torso(rig)
        shirt=tree(np.array(garment["positions"]),np.array(garment["triangles"]))
        for name,case in cases.items():
            row=routes[name]
            if rig!=row["rig"]:continue
            if saved:
                h,ht=meshbuffers(Path(levels[row["mesh"]]["levels"]["render0"]["folder"]),"faces.bin")
                shell,st=meshbuffers(Path(levels[row["rigid"]]["levels"]["source0"]["folder"]),"faces.bin")
            else:
                h=np.fromfile(F/(row["mesh"].rsplit("/",1)[-1]+".bin"),"<f4").reshape(-1,3)
                ht=np.fromfile(Path(case["donor"]["source_harness_directory"])/"triangles.bin","<i4").reshape(-1,3)
                shell,st=meshbuffers(Path(case["donor"]["source_shell_directory"]),"triangles.bin")
            q=row["rigid_rotation_quat"]
            shell=shell@np.asarray(Quaternion((q[3],*q[:3])).to_matrix()).T+row["rigid_location"]
            shell_tree=tree(shell,st)
            ends=np.array(seams[name]["authored_sewn_cap_centres"])
            caps=np.array([h[np.argmin(np.linalg.norm(h-p,axis=1))] for p in ends])
            gaps=[float(shell_tree.find_nearest(Vector(p))[3]) for p in caps]
            measures=dict(garment_harness_pairs=len(shirt.overlap(tree(h,ht))),
                          garment_cargo_pairs=len(shirt.overlap(shell_tree)),
                          seam_end_nearest_shell_cm=gaps,maximum_seam_distance_cm=max(gaps),
                          cap_to_authored_displacement_cm=float(np.linalg.norm(caps-ends,axis=1).max()))
            print(name,measures,flush=True);record[name]=measures
    (F/("saved-seams.json" if saved else "authored-seams.json")).write_text(json.dumps(record,indent=2))
    if any(q["garment_harness_pairs"] or q["garment_cargo_pairs"] or q["maximum_seam_distance_cm"]>.11 or q["cap_to_authored_displacement_cm"]>.005 for q in record.values()):
        raise ValueError("Further seam refit required")


if __name__=="__main__":main("--saved" in sys.argv)
