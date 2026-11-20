"""Measure the fitted fingers on captured native poses using the equipped UE meshes."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree
from trimesh.triangles import closest_point,points_to_barycentric

from native_glove_review import Skin,component
from native_glove_author import frames

P=Path(__file__).resolve().parents[2]
SET=P/"SourceAssets/ModernTacticalSet20261113"
R=SET/"CoyoteGlovesR2"
REVIEW=R/"Review"


def read(path):
    return json.loads(path.read_bytes())


def digest(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file,"sha256").hexdigest()


def thumb_panel_edges(glove):
    # UE may reorder or split vertices at tangents and seams. Match the actual
    # saved triangles to the sewing pattern before measuring their posed edges.
    pattern=read(R/"Authored/gloves_Super90.json")
    start,end=pattern["parts"]["r_Thumb_lock_wrap"]
    triangles=np.asarray(pattern["positions"])[np.asarray(pattern["triangles"])[start:end]]
    saved=glove.points[glove.faces]
    tree=cKDTree(saved.mean(1))
    _,candidates=tree.query(triangles.mean(1),k=4)
    delta=saved[candidates][:,:,None,:,:]-triangles[:,None,:,None,:]
    error=np.linalg.norm(delta,axis=-1).min(3).max(2)
    match=np.argmin(error,axis=1)
    idx=np.arange(len(candidates))
    if error[idx,match].max()>.001:
        raise ValueError("The saved thumb patch no longer matches the current sewing pattern")
    faces=glove.faces[candidates[idx,match]]
    edges=np.concatenate((faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]))
    return np.unique(np.sort(edges,axis=1),axis=0)


def anatomical_anchors(skin,glove,slots):
    # Use the primary finger fabric, including the leather fingertip caps.
    # Wrist closures, labels and the volume of the cuff are outside this measure.
    groups=[i for i,name in enumerate(slots) if any(k in name.lower() for k in ("knit","suede","stretch"))]
    face_mask=np.isin(glove.mats,groups)
    garment=np.unique(glove.faces[face_mask])
    coords,anchors,weights,labels=[],[],[],[]
    for region in sorted(set(glove.zones[garment])):
        if region.rsplit("/",1)[-1]=="palm":
            continue
        pts=garment[glove.zones[garment]==region]
        _,unique=np.unique(np.round(glove.points[pts],4),axis=0,return_index=True)
        pts=pts[np.sort(unique)]
        # Uniform deterministic sampling with a per-finger cap.
        if len(pts)>1000:
            pts=pts[np.linspace(0,len(pts)-1,1000).astype(int)]
        tri=skin.faces[np.any(skin.zones[skin.faces]==region,axis=1)]
        pos=skin.points[tri]
        tri=tri[np.linalg.norm(np.cross(pos[:,1]-pos[:,0],pos[:,2]-pos[:,0]),axis=1)>1.e-6]
        tree=cKDTree(skin.points[tri].mean(1))
        for batch in np.array_split(pts,max(1,int(np.ceil(len(pts)/256)))):
            hits=tri[tree.query(glove.points[batch],k=min(16,len(tri)))[1]]
            pr=closest_point(skin.points[hits].reshape(-1,3,3),np.repeat(glove.points[batch],hits.shape[1],axis=0)).reshape(len(batch),-1,3)
            best=np.argmin(np.linalg.norm(pr-glove.points[batch,None],axis=2),axis=1)
            ids=hits[np.arange(len(batch)),best];p=pr[np.arange(len(batch)),best]
            w=points_to_barycentric(skin.points[ids],p).clip(0,1)
            coords.extend(batch);anchors.extend(ids);weights.extend(w/w.sum(1,keepdims=True));labels.extend([region]*len(batch))
    if len(set(labels))!=10:
        raise ValueError("The fitted model must supply left and right samples for all five fingers")
    return np.array(coords),np.array(anchors),np.array(weights),np.array(labels)


def evaluate(gun,authored=False):
    rig="Super90" if gun in ("M870","Super90") else gun
    ref=SET/"NativeGloveR1"
    refs=(ref if rig=="Super90" else ref/rig)/"Read"
    model_file=R/"Authored"/f"gloves_{rig}.json" if authored else REVIEW/"Read"/f"{rig}.json"
    model=read(model_file);native=read(refs/f"{gun}_Jason.json")
    package=lambda value:P/"Content"/(value.split(".")[0].removeprefix("/Game/")+".uasset")
    if (not authored and digest(package(model["source"]))!=model["asset_sha256"]) or digest(package(native["source"]))!=native["asset_sha256"]:
        raise RuntimeError(f"Pose review geometry has changed on disk for {gun}")
    pose_file=refs/f"{gun}_poses.json.gz"
    data=json.load(gzip.open(pose_file,"rt"));names=data["names"]
    parents=[names.index(parent) if parent in names else -1 for parent in data["parents"]]
    glove=Skin(model,names,False);skin=Skin(native,names,False)
    edges=thumb_panel_edges(glove) if gun=="M870" else None
    if edges is not None:
        rest_lengths=np.linalg.norm(glove.points[edges[:,1]]-glove.points[edges[:,0]],axis=1)
    ids,tris,w,labels=anatomical_anchors(skin,glove,model["material_slots"])
    weights=w[:,:,None]
    rest=skin.points[tris];rest_anchor=(rest*weights).sum(1)
    # Express each sampled cloth point's thickness in the local tangent frame
    # of its own native finger. Rebuild that point from the same posed triangle.
    local=np.einsum("nij,ni->nj",frames(rest),glove.points[ids]-rest_anchor)
    output={}
    for name,clip in data["clips"].items():
        seq=package(clip["path"])
        if seq.stat().st_mtime>pose_file.stat().st_mtime+2:
            raise RuntimeError("The animation was saved since capture: "+clip["path"])
        worst=(0.,0.,0.);sample=0;by_digit={k:0. for k in np.unique(labels)}
        max_stretch=0.
        for i,packed in enumerate(clip["local"]):
            pose=component(packed,parents)
            deform=skin.skin(pose)[tris]
            q=(deform*weights).sum(1)+np.einsum("nij,nj->ni",frames(deform),local)
            garment=glove.skin(pose)
            drift_mm=10*np.linalg.norm(garment[ids]-q,axis=1)
            if edges is not None:
                lengths=np.linalg.norm(garment[edges[:,1]]-garment[edges[:,0]],axis=1)
                max_stretch=max(max_stretch,float(np.max(lengths-rest_lengths))*10.)
            pct=np.percentile(drift_mm,[95,99,100])
            if pct[0]>worst[0]:
                sample=i
            worst=np.maximum(worst,pct)
            for key in by_digit:
                by_digit[key]=max(by_digit[key],float(np.percentile(drift_mm[labels==key],95)))
        output[name]=dict(frames=len(clip["local"]),worst_p95_frame=sample,peak_p95_mm=round(float(worst[0]),3),
                          peak_p99_mm=round(float(worst[1]),3),maximum_mm=round(float(worst[2]),3),
                          per_finger_peak_p95_mm={k:round(v,3) for k,v in by_digit.items()})
        if edges is not None:
            output[name]["maximum_thumb_panel_edge_extension_mm"]=round(max_stretch,3)
    result=dict(gun=gun,source=model_file.relative_to(R).as_posix() if authored else model["source"],source_sha256=digest(model_file),
                package_sha256=None if authored else model["asset_sha256"],poses_sha256=digest(pose_file),
                finger_points=len(ids),rest_distance_to_native_surface_p95_mm=round(float(np.percentile(np.linalg.norm(local,axis=1),95)*10),3),
                method="Per-point residual against its corresponding skinned native finger triangle with rest thickness and tangent direction retained. 12Hz offline native sequence sampling, no gameplay or physics.",
                clips=output,frames=sum(v["frames"] for v in output.values()))
    suffix="-authored" if authored else ""
    path=REVIEW/f"{gun}-finger-pose{suffix}.json";path.write_text(json.dumps(result,indent=2),encoding="utf8")
    print(gun,len(output),result["frames"],max(i["peak_p95_mm"] for i in output.values()),flush=True)


if __name__=="__main__":
    arg=argparse.ArgumentParser();arg.add_argument("gun",choices=("M870","Super90","M16"))
    arg.add_argument("--authored",action="store_true");options=arg.parse_args()
    evaluate(options.gun,options.authored)
