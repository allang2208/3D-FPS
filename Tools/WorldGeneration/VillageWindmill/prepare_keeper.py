"""Fit the original Meshy surface to Kaitlin's weighted neckline and tailor the work clothes."""
import json
from itertools import product
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree
from keeper_neckline import shoulder_panel, finish_neckline
from keeper_fabrics import material_paths

PROJECT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT / "Tools/VillageBaker"))
from assemble import source_surface, points_of_fit, crop, ring, interpolate, bridge_faces, unit

ROOT = PROJECT / "SourceAssets/HillsVillageWindmill/MillKeeper/CharacterR1"
OUT = ROOT / "Assembly"
DONOR = PROJECT / "SourceAssets/ChapelNun20261115"
INPUT = DONOR / "ProductionR1/Inputs"
BAKER = "/Game/Characters/VillageBaker/Materials/M_Baker_"
MATS = {}


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def petite(points):
    p = np.array(points, dtype=float)
    z = p[:, 2].copy()
    p[:, 0] *= np.interp(z, [0, 70, 95, 130, 144, 152], [.91, .89, .855, .865, .905, .95])
    p[:, 1] *= np.interp(z, [0, 90, 114, 140, 152], [.925, .855, .84, .88, .95])
    p[:, 2] = np.interp(z, [0, 44, 90, 140, 168.8, 190], [0, 40, 82, 128, 155, 175])
    return p


def part(name, p, tri, uv, weights, material_ids, material_names, normals=None):
    triangles = np.asarray(tri, dtype=int)
    unique, ix = np.unique(triangles, return_inverse=True)
    w = np.zeros((len(unique), 8), np.float32)
    joints = np.zeros_like(w, np.int16)
    for i, idx in enumerate(unique):
        row = weights[idx]
        pairs = sorted(((b, a) for b, a in (row.items() if isinstance(row, dict) else row) if a > 1e-5),
                       key=lambda x: -x[1])[:8]
        total = sum(a for b, a in pairs)
        for j, (b, a) in enumerate(pairs):
            joints[i,j], w[i,j] = b, a/total
    payload = dict(p=petite(np.asarray(p)[unique]), tri=ix.reshape(-1,3), uv=uv, w=w, j=joints,
                   mats=material_names, ids=material_ids)
    if normals is not None:
        payload["n"] = normals
    np.savez(OUT / (name+".npz"), **payload)


def garment(name, data, replacements, keep=None):
    tri = np.asarray(data["triangles"]); ids = np.asarray(data["triangle_materials"])
    mask = np.isin(ids, list(replacements))
    if keep is not None: mask &= keep
    names = list(dict.fromkeys(replacements.values()))
    part(name, data["positions"], tri[mask], np.asarray(data["uv"])[mask], data["weights"],
         [names.index(replacements[i]) for i in ids[mask]], names, np.asarray(data["normals"])[mask])


def work_dress():
    # This capture has both hood shells removed. Its triangle IDs already refer
    # to the original material slots, including the surviving torso lining.
    robe = read(DONOR / "IdleBackReviewR2/InputsAfter/robe.json")
    fabrics = {"RobeBody": "WorkLinen", "RobeSleeves": "WorkLinen", "RobeCuffs": "Cuff",
               "SleeveLining": "Cuff", "RobeSkirt": "Skirt", "RobeBelt": "Belt",
               "TorsoLining": "WorkLinen", "RobeEmbroidery": "NeckLinen"}
    slots = [material["slot"] for material in robe["materials"]]
    garment("Dress", robe, {slots.index(slot): fabric for slot, fabric in fabrics.items()},
            shoulder_panel(robe, slots.index("RobeEmbroidery")))
    finish_neckline(OUT/"Dress.npz", OUT/"Head.npz")


def complete_body():
    # The saved player's full body and its UV islands are separate captures.
    data=read(PROJECT/"SourceAssets/ST6FemaleCollar20261108/Inputs/body.json")
    choices=read(PROJECT/"SourceAssets/KaitlinPlayer20261023/kaitlin_body_uv.json")["vertex_uvs"]
    tri=np.asarray(data["triangles"])
    first=np.array([choices[str(i)][0] for i in range(len(data["positions"]))])
    uv=first[tri]
    split=np.array([len(choices[str(i)])>1 for i in range(len(first))])
    for ix in np.flatnonzero(split[tri].any(axis=1)):
        alternatives=np.asarray(list(product(*(choices[str(v)] for v in tri[ix]))))
        perimeter=((alternatives-np.roll(alternatives,1,axis=1))**2).sum(axis=(1,2))
        uv[ix]=alternatives[np.argmin(perimeter)]
    z=np.asarray(data["positions"])[tri,2].mean(axis=1)
    ids=np.asarray(data["triangle_materials"])
    # Opaque base layers cover the torso and upper legs on the editable body.
    mat=np.where(np.isin(ids,[1,2,5]) | (z<47),0,np.where(z>=91,1,2))
    part("Base",data["positions"],tri,uv,data["weights"],mat,["Hands","WorkLinen","Skirt"])


def head(body):
    target = read(INPUT / "native_head.json")
    p, n, uv, tri, maps = source_surface(ROOT/"MeshyHead/head.glb", OUT, "MillKeeper")
    crown, nose = points_of_fit(p)
    # The apex includes the middle part. Use the actual nose/crown distances on Kaitlin.
    p = (p-nose)*((168.8-153.4)/(crown-nose[2])) + [0,13.3,153.4]
    cut = max(142.4,float(p[:,2].min())+.55)
    if cut > 148.5: raise ValueError("Meshy bust ends above the native neck")
    native = np.asarray(target["positions"]); faces = np.asarray(target["triangles"])
    mask = np.asarray(target["triangle_materials"])==0
    f = faces[mask]
    corners, ids = np.unique(np.column_stack((f.ravel(),np.asarray(target["uv"])[mask].reshape(-1,2),
                             np.asarray(target["normals"])[mask].reshape(-1,3))),axis=0,return_inverse=True)
    bones = {b["name"]:b["index"] for b in body["bones"]}
    remap=[]
    for b in target["bones"]:
        while b["name"] not in bones: b=target["bones"][b["parent"]]
        remap.append(bones[b["name"]])
    weights=[]
    for row in target["weights"]:
        out={}
        for b,w in row:
            if w>0: out[remap[b]]=out.get(remap[b],0)+w
        weights.append(out)
    idx=corners[:,0].astype(int)
    lp,ln,lu,lw,lf,le=crop(native[idx],corners[:,3:],corners[:,1:3],[weights[i] for i in idx],
                            ids.reshape(-1,3),cut-.16,False)
    prox=cKDTree(native).query(p)[1]
    hw=[weights[i] if z<148 else {bones["head"]:1.} for i,z in zip(prox,p[:,2])]
    hp,hn,hu,hw,hf,he=crop(p,n,uv,hw,tri,cut,True)
    center=np.median(lp[le],axis=0)
    la,li=ring(lp,le,center); ha,hi=ring(hp,he,center)
    theta=np.arctan2(hp[:,1]-center[1],hp[:,0]-center[0])
    dest=np.column_stack([np.interp(theta,la,lp[li,ax],period=2*np.pi) for ax in (0,1)])
    fade=np.clip((cut+2.3-hp[:,2])/2.3,0,1);fade=fade*fade*(3-2*fade)
    hp[:,:2]+=(dest-hp[:,:2])*fade[:,None]
    tree=cKDTree(lp[li,:2])
    for i in np.flatnonzero(fade):
        k=li[tree.query(hp[i,:2])[1]]
        hw[i]=interpolate(hw[i],lw[k],fade[i]);hn[i]=unit(hn[i]*(1-fade[i])+ln[k]*fade[i])
    stitch=bridge_faces(hp[hi],lp[li],ha,la)
    seam=np.r_[hi,li+len(hp)][stitch]
    seam_uv=np.vstack((lu[li[tree.query(hp[hi,:2])[1]]],lu[li]))[stitch]
    faces=np.vstack((hf,lf+len(hp),seam))
    names=["KeeperFace"+str(i) for i in range(len(maps))]+["NeckLinen"]
    for name,atlas in zip(names,maps): MATS[name]={k:Path(v).name for k,v in atlas.items()}
    MATS["NeckLinen"]=BAKER+"Cuff"
    part("Head",np.vstack((hp,lp)),faces,np.concatenate((hu[hf,:2],lu[lf],seam_uv)),hw+lw,
         np.r_[hu[hf[:,0],2].astype(int),np.full(len(lf)+len(seam),len(maps))],names,
         np.vstack((hn,ln))[faces])
    return dict(crown_cm=float(petite(p)[:,2].max()),neck_cm=cut,bridge_triangles=len(seam))


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    body=read(INPUT/"native_body.json")
    complete_body()
    MATS["Hands"]=body["materials"][2]["asset"]
    garment("Body",body,{2:"Hands",1:"Hands"},np.min(np.asarray(body["positions"])[np.asarray(body["triangles"]),2],axis=1)<102.5)
    MATS.update(WorkLinen=BAKER+"Shirt",Cuff=BAKER+"Cuff",Skirt=BAKER+"Pants",Belt=BAKER+"Sash")
    boots=read(DONOR/"BootFinishR8/Authored/boots.json")
    MATS.update(Leather=BAKER+"Boot",Sole=BAKER+"Sole",Thread=BAKER+"Thread")
    garment("Boots",boots,{0:"Belt",1:"Leather",2:"Sole",3:"Thread",4:"Leather",5:"Leather",6:"Leather",7:"Skirt"},
            np.min(np.asarray(boots["positions"])[np.asarray(boots["triangles"]),2],axis=1)<32.)
    del boots
    info=head(body)
    work_dress()
    MATS.update(material_paths())
    rig=read(DONOR/"IdleRelaxedR3/authored.json")
    np.savez(OUT/"Rig.npz",positions=petite([b["position"] for b in body["bones"]]),
             axes=[b["axes"] for b in body["bones"]], names=rig["names"], parents=rig["parents"],
             reference=rig["reference"], idle=np.asarray(rig["frames"])[::3])
    (OUT/"assembly.json").write_text(json.dumps(dict(**info,materials=MATS,body=body["source"],
        base_body=read(INPUT/"native_recipe.json")["base_body"],skeleton=body["skeleton"],
        meshy_task=read(ROOT/"MeshyHead/task.json")["id"]),indent=2))


if __name__=="__main__":
    main()
