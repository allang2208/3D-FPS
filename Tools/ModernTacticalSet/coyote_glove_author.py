"""Author fitted MG-72-inspired TS01 gloves on every selected native skin."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from coyote_glove_author_surface import P,SET,OUT,SLOTS,Shell,Hand,read,write,unit,input_file
from coyote_glove_author_patterns import Atelier


DEST="/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CoyoteGlovesR2"
ITEM="ue_modern_tactical_gloves"


def active():
    cfg=read(P/"Content/ColdSteelData/modular_outfits.json")
    plan=read(OUT.parent/"Wear/plan.json")["rigs"]
    result={}
    for rig,group in (("Jason",cfg),("Kaitlin",cfg["body_variants"]["kaitlin"])):
        for key,asset in group["items"][ITEM]["rig_meshes"].items():
            previous=plan[key]["previous"]
            if asset not in (previous,plan[key]["asset"]):
                raise ValueError(f"Unexpected glove route for {rig}/{key}")
            row=result.setdefault(key,dict(source=previous,owners=[]))
            row["owners"].append(rig)
    return result


def skin_weights(shell,tri,bary):
    rows=[]
    for vv,coeff in zip(tri,bary):
        weights={}
        for vi,c in zip(vv,coeff):
            for idx,w in shell.ws[vi]:
                weights[idx]=weights.get(idx,0.)+c*w
        contributions=sorted(((i,w) for i,w in weights.items() if w>1.e-7),key=lambda pair:-pair[1])[:8]
        scale=sum(w for _,w in contributions)
        rows.append([[i,round(float(w/scale),8)] for i,w in contributions])
    return rows


def finish_part(shell,part,mapping,corners):
    source_ids=part["anchor"];face=mapping[source_ids]
    if (face<0).any():raise ValueError("Unmapped surface triangle on "+part["name"])
    perm=corners[source_ids];tri=np.take_along_axis(shell.f[face],perm,axis=1)
    ns=np.take_along_axis(shell.ns[face],perm[:,:,None],axis=1)
    w=part["w"]
    n=unit(np.einsum("ij,ijk->ik",w,ns))
    p=np.einsum("ij,ijk->ik",w,shell.p[tri])+n*part["height"][:,None]
    f=part["faces"].copy()
    pp=p[f];cross=np.cross(pp[:,1]-pp[:,0],pp[:,2]-pp[:,0])
    keep=np.linalg.norm(cross,axis=1)>1.e-8
    f=f[keep];cross=cross[keep]
    rev=np.einsum("ij,ij->i",cross,n[f].mean(1))>0
    f[rev]=f[rev,::-1];cross[rev]*=-1
    cn=np.zeros(p.shape)
    for c in range(3):np.add.at(cn,f[:,c],-cross)
    cn=unit(cn);bad=np.linalg.norm(cn,axis=1)<.1;cn[bad]=n[bad]
    return p,f,cn[f],part["uv"][f],skin_weights(shell,tri,w)


def canonical(rig):
    shell=Shell(rig);mat=np.zeros(len(shell.f),int);uv=np.zeros((len(shell.f),3,2))
    parts=[]
    for side in ("r","l"):
        h=Hand(shell,side);a=Atelier(h)
        mat[h.ids]=h.mat;uv[h.ids]=h.uv
        parts.extend(a.cut())
    return shell,mat,uv,parts


_masters={}


def author(job):
    rig,info=job;kind=rig if rig in ("Jason","Kaitlin") else "M4"
    if kind not in _masters:_masters[kind]=canonical(kind)
    base,mat,uv,parts=_masters[kind]
    shell=base if rig==kind else Shell(rig)
    sides=set(shell.sideface)
    mapping,corner,base_for,base_corner=shell.map_from(base,sides)
    if (base_for<0).any():raise ValueError(f"Unclassified shell face on {rig}")
    d=shell.src
    p=[shell.p];f=[shell.f];weights=list(shell.ws)
    normal=[shell.ns];tex=[np.take_along_axis(uv[base_for],base_corner[:,:,None],axis=1)]
    m=[mat[base_for]]
    ranges={"Native_cloth_shell":[0,len(shell.f)]};first=len(shell.f);vcount=len(shell.p)
    for part in parts:
        if part["side"] not in sides:continue
        if ((kind=="M4" and part["name"]=="l_Thumb_lock_wrap") or
                (rig=="Super90" and part["name"]=="r_Thumb_lock_wrap")):
            from coyote_glove_thumb_cut import cut_supported_thumb
            part=cut_supported_thumb(base,shell,part,mapping,corner)
        pp,ff,nn,uu,ww=finish_part(shell,part,mapping,corner)
        p.append(pp);f.append(ff+vcount);normal.append(nn);tex.append(uu)
        m.append(np.full(len(ff),part["mat"],int));weights.extend(ww)
        ranges[part["name"]]=[first,first+len(ff)];first+=len(ff);vcount+=len(pp)
    filename=OUT/f"gloves_{rig}.json"
    triangles=np.vstack(f);slots=np.concatenate(m)
    materials=[DEST+"/Materials/M_"+s+".M_"+s for s in SLOTS]
    out=dict(source=info["source"],skeleton=d["skeleton"],rig=rig,bones=d["bones"],
             positions=np.vstack(p).round(6).tolist(),triangles=triangles.tolist(),weights=weights,
             normals=np.concatenate(normal).round(6).tolist(),uv=np.concatenate(tex).round(6).tolist(),
             material_slots=SLOTS,materials=materials,triangle_materials=slots.tolist(),parts=ranges)
    write(filename,out)
    asset_name="SK_TS01_CoyoteGloves_"+rig
    row=dict(rig=rig,source=info["source"],file=str(filename),asset=f"{DEST}/Wear/{rig}/{asset_name}.{asset_name}",
             owners=info["owners"],triangles=len(triangles),vertices=vcount,parts=len(ranges),
             source_sha256=hashlib.sha256(filename.read_bytes()).hexdigest(),
             native_shell_vertices=len(shell.p),native_shell_triangles=len(shell.f),
             source_file=str(input_file(rig)),material_faces={s:int(np.sum(slots==i)) for i,s in enumerate(SLOTS)})
    if rig in ("Jason","Kaitlin"):
        row["native_body_skin"]=str(SET/"CombatShirtR3/CuffRepairR1/Inputs"/f"Body_{rig}.json")
    write(OUT/(rig+"-source.json"),row);print("COYOTE_AUTHORED",rig,len(triangles),vcount,flush=True)
    return row


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--jobs",type=int,default=3);ap.add_argument("rig",nargs="*")
    opt=ap.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    records=active();keys=opt.rig or list(records)
    work=[(k,records[k]) for k in keys]
    if opt.jobs==1:
        for item in work:author(item)
    else:
        with ProcessPoolExecutor(max_workers=opt.jobs) as pool:list(pool.map(author,work))
    if all((OUT/(k+"-source.json")).is_file() for k in records):
        rows=[read(OUT/(k+"-source.json")) for k in records]
        write(OUT/"routes.json",dict(completed=True,item=ITEM,rows=rows,material_slots=SLOTS,
              reference="https://www.mechanix.com/us-en/tactical-and-military-gloves/MG-72-008.html"))


if __name__=="__main__":main()
