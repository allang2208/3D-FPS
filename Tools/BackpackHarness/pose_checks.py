"""Requested representative posed-clothing contact checks and render inputs."""
from pathlib import Path
import numpy as np
import trimesh
from author import R,I,read,write,visible_mesh
from validate import skin,edge_hits

poses=read(I/"poses.json")
manifest=read(R/"manifest.json")
reports=[]
def torso_surface(data):
    mesh=visible_mesh(data)
    arm={b["index"] for b in data["bones"] if b["name"].startswith(("upperarm","lowerarm","hand","thumb","index","middle","ring","pinky"))}
    influence=np.array([sum(w for b,w in row if b in arm) for row in data["weights"]])
    keep=influence[mesh.faces].mean(axis=1)<.5
    return trimesh.Trimesh(mesh.vertices,mesh.faces[keep],process=False)
for profile in ("knit_sweater","mage_robe"):
    row=next(r for r in manifest["variants"] if r["profile"]==profile)
    data=read(Path(row["source"]));body=read(I/"body.json");cloth=read(I/(row["shirt"]+".json"))
    for key,clip in poses["clips"].items():
        if profile=="mage_robe" and key not in ("Unarmed.Idle","Staff.FullBody.CastRelease"):
            continue
        sample=clip["frames"][2]
        pack_pose=skin(data,sample["bones"],poses["reference"])
        body_pose=skin(body,sample["bones"],poses["reference"])
        cloth_pose=skin(cloth,sample["bones"],poses.get("mesh_references",{}).get(row["shirt"],poses["reference"]))
        posed_body=dict(body,positions=body_pose.tolist())
        posed_cloth=dict(cloth,positions=cloth_pose.tolist())
        target=trimesh.util.concatenate([visible_mesh(posed_body),visible_mesh(posed_cloth)])
        hits=edge_hits(pack_pose[:data["harness_vertex_count"]],
                       np.asarray(data["triangles"][:data["harness_face_count"]]),target)
        torso=trimesh.util.concatenate([torso_surface(posed_body),torso_surface(posed_cloth)])
        torso_hits=edge_hits(pack_pose[:data["harness_vertex_count"]],
                            np.asarray(data["triangles"][:data["harness_face_count"]]),torso)
        result={"profile":profile,"clip":key,"time":sample["time"],**hits,
                "torso_intersecting_edges":torso_hits["intersecting_edges"],"torso_locations":torso_hits["locations"]}
        reports.append(result)
        if key=="Unarmed.Idle":
            directory=R/"PoseViews"/profile;directory.mkdir(parents=True,exist_ok=True)
            write(directory/"pack.json",dict(data,positions=pack_pose.tolist()))
            write(directory/"body.json",posed_body);write(directory/"cloth.json",posed_cloth)
        print("HARNESS_POSED_CONTACT",result,flush=True)
write(R/"posed_contacts.json",{"samples":reports,"scope":"compressed source poses with linear blend skinning; no Chaos cloth simulation"})
