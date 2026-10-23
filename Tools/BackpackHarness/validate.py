"""Requested AUTHOR-space topology, clothing intersections and source poses.

Author faces use cross(e1,e2). This is not UE facing validation: save.py must
convert corners, and saved facing is checked against UE's own cube render data.
"""
import json
import hashlib
from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation
from author import I, R, PROFILES, visible_mesh, read, write


def matrix(value):
    out=np.eye(4)
    out[:3,:3]=Rotation.from_quat(value[3:7]).as_matrix() @ np.diag(value[7:10])
    out[:3,3]=value[:3]
    return out


def skin(data, pose, reference):
    vertices=np.asarray(data["positions"],float)
    result=np.zeros_like(vertices)
    rows={}
    names={b["index"]:b["name"] for b in data["bones"]}
    for vi,weights in enumerate(data["weights"]):
        for bi,weight in weights:
            if weight>0:
                rows.setdefault(names[bi],[]).append((vi,weight))
    for name,pairs in rows.items():
        if name not in pose or name not in reference:
            raise RuntimeError("Missing native bone "+name)
        transform=matrix(pose[name]) @ np.linalg.inv(matrix(reference[name]))
        ids=np.array([p[0] for p in pairs]);weights=np.array([p[1] for p in pairs])
        result[ids]+=(vertices[ids]@transform[:3,:3].T+transform[:3,3])*weights[:,None]
    return result


def edge_hits(v, t, target):
    corners=target.triangles
    overlap=np.all(corners.max(axis=1)>=v.min(axis=0)-.01,axis=1)&np.all(corners.min(axis=1)<=v.max(axis=0)+.01,axis=1)
    target=trimesh.Trimesh(target.vertices,target.faces[overlap],process=False)
    edges=np.unique(np.sort(np.vstack([t[:,[0,1]],t[:,[1,2]],t[:,[2,0]]]),axis=1),axis=0)
    starts=v[edges[:,0]]
    delta=v[edges[:,1]]-starts
    lengths=np.linalg.norm(delta,axis=1)
    directions=delta/np.maximum(lengths[:,None],1e-10)
    points,rays,_=target.ray.intersects_location(starts+directions*.002,directions,multiple_hits=False)
    distance=np.linalg.norm(points-starts[rays],axis=1)
    hits=rays[(distance>.004)&(distance<lengths[rays]-.004)]
    return {"intersecting_edges":len(np.unique(hits)),
            "locations":np.round(v[edges[hits[:12]]].mean(axis=1),3).tolist()}


def run():
    poses=read(I/"poses.json")
    manifest=read(R/"manifest.json")
    report={}
    passed=True
    for row in manifest["variants"]:
        profile=row["profile"]
        d=read(Path(row["source"]))
        nv,nf=d["harness_vertex_count"],d["harness_face_count"]
        v=np.asarray(d["positions"]);t=np.asarray(d["triangles"],int)
        ht=t[:nf];hv=v[:nv]
        mesh=trimesh.Trimesh(hv,ht,process=False)
        parts=mesh.split(only_watertight=False)
        uv=np.asarray(d["uv"][:nf])
        a,b=uv[:,1]-uv[:,0],uv[:,2]-uv[:,0]
        uv_zero=int((abs(a[:,0]*b[:,1]-a[:,1]*b[:,0])<1e-10).sum())
        area=np.linalg.norm(np.cross(hv[ht[:,1]]-hv[ht[:,0]],hv[ht[:,2]]-hv[ht[:,0]]),axis=1)
        normals=np.asarray(d["normals"][:nf])
        fn=mesh.face_normals
        opposed=int((np.einsum("ij,ij->i",normals.mean(axis=1),fn)<-.01).sum())
        skin_sums=np.array([sum(w for _,w in pairs) for pairs in d["weights"]])
        paths=[]
        bag_surface=trimesh.Trimesh(v,t[nf:],process=False)
        for part in d["parts"]:
            if not part["name"].startswith("shoulder_return"):
                continue
            path=np.asarray(part["path"]);base=np.asarray(part["base_path"])
            ratio=np.linalg.norm(np.diff(path,axis=0),axis=1)/np.linalg.norm(np.diff(base,axis=0),axis=1)
            _,sewn_distance,_=bag_surface.nearest.on_surface(path[[0,-1]])
            paths.append({"name":part["name"],"max_adjacent_stretch":float(ratio.max()),
                          "max_adjacent_cm":float(np.linalg.norm(np.diff(path,axis=0),axis=1).max()),
                          "anchor_error_cm":float(np.max(sewn_distance)),
                          "front_lowest_cm":float(path[path[:,1]>8,2].min()),
                          "return_sag_cm":float(path[:,2].min()-path[-1,2])})
        body=read(I/"body.json")
        cloth=read(I/(row["shirt"]+".json")) if row["shirt"] else body
        targets=trimesh.util.concatenate([visible_mesh(body),visible_mesh(cloth)]) if row["shirt"] else visible_mesh(body)
        intersections=edge_hits(hv,ht,targets)
        envelope=read(R/"Envelopes"/(profile+".json"))
        exterior=np.min([(hv@np.asarray(equation)[:,:3].T+np.asarray(equation)[:,3]).max(axis=1)
                         for equation in envelope["cells"]],axis=0)
        edges=np.unique(np.sort(np.vstack([ht[:,[0,1]],ht[:,[1,2]],ht[:,[2,0]]]),axis=1),axis=0)
        rest_length=np.linalg.norm(hv[edges[:,0]]-hv[edges[:,1]],axis=1)
        harness_data=dict(d,positions=d["positions"][:nv],weights=d["weights"][:nv])
        pose_rows=[]
        for key,clip in poses["clips"].items():
            for sample in clip["frames"]:
                posed=skin(harness_data,sample["bones"],poses["reference"])
                length=np.linalg.norm(posed[edges[:,0]]-posed[edges[:,1]],axis=1)
                stretch=length/np.maximum(rest_length,1e-8)
                pose_rows.append({"clip":key,"time":sample["time"],"max_edge_stretch":float(stretch.max()),
                                  "p99_edge_stretch":float(np.percentile(stretch,99)),
                                  "finite":bool(np.isfinite(posed).all())})
        good=(np.isfinite(v).all() and all(p.is_watertight and p.volume>0 for p in parts)
              and not uv_zero and not opposed and area.min()>1e-7
              and np.max(abs(skin_sums-1))<1e-5 and intersections["intersecting_edges"]==0
              and exterior.min()>=-1e-4 and all(p["max_adjacent_stretch"]<2. and p["max_adjacent_cm"]<1.3 and p["anchor_error_cm"]<.3 for p in paths)
              and all(p['front_lowest_cm']>=118.5 and p['return_sag_cm']>=-.3 for p in paths)
              and all(p["finite"] and p["max_edge_stretch"]<2 for p in pose_rows))
        passed &= bool(good)
        report[profile]={"pass":bool(good),"source_sha256":hashlib.sha256(Path(row["source"]).read_bytes()).hexdigest(),
                         "closed_components":sum(p.is_watertight for p in parts),
                         "components":len(parts),"positive_volume":all(p.volume>0 for p in parts),
                         "uv_degenerate":uv_zero,"normal_opposed":opposed,"min_double_area":float(area.min()),
                         "max_weight_sum_error":float(np.max(abs(skin_sums-1))),
                         "envelope_min_cm":float(exterior.min()),"actual_surface":intersections,
                         "paths":paths,"pose_samples":pose_rows}
        print("HARNESS_CHECK",profile,json.dumps({k:val for k,val in report[profile].items() if k not in ("pose_samples","paths")}),flush=True)
    write(R/"checks.json",{"pass":passed,"variants":report,"scope":"author geometry + current saved clothing + 24 compressed source poses; no live cloth or multiplayer"})
    if not passed:
        raise SystemExit(1)


if __name__=="__main__":
    run()
