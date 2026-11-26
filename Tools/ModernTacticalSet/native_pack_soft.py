"""Restore the original soft cargo volume and connect the two native strap ends to it."""
from pathlib import Path
import json

import numpy as np
from scipy.interpolate import RegularGridInterpolator
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
from trimesh.triangles import closest_point

from native_pack_rigid_author import CURRENT, DEST, REV, BASE, coords, derive, geometry, read, repair

OUT=BASE/REV/"Soft"


def write(name,data):
    (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")


def edges(points,faces):
    t=points[faces]
    return np.linalg.norm(t-np.roll(t,1,axis=1),axis=2).max(axis=1)


def safe_shift(rig,points,faces):
    field=np.load(CURRENT/"Surfaces"/(rig+"_ue_modern_kevlar_vest.npz"))
    frame=read(CURRENT/"Surfaces/frames.json")[rig]
    matrix=np.asarray(frame["matrix"])
    grid=RegularGridInterpolator((field["xs"],field["zs"]),field["guarded_rear"],bounds_error=False,fill_value=np.nan)
    samples=np.concatenate((points[np.unique(faces)],points[faces].mean(axis=1)))
    norm=(samples-frame["translation"])@matrix.T
    gap=grid(norm[:,[0,2]])-norm[:,1]
    shift=max(0.,(.40-np.nanmin(gap))/max(.94,matrix[1,1]))
    return np.array([0.,-shift,0.])


def straps(original,current,faces,mask,cargo,shift,cargo_faces):
    keep=np.flatnonzero(~cargo)
    reverse=np.full(len(original),-1);reverse[keep]=np.arange(len(keep))
    sf=reverse[faces[~cargo[faces].any(axis=1)]]
    source=original[keep];fit=current[keep];weights=mask[keep]
    unique,inv=np.unique(np.round(source,4),axis=0,return_inverse=True)
    fc=inv[sf];e=np.concatenate([fc[:,[0,1]],fc[:,[1,2]],fc[:,[2,0]]])
    graph=coo_matrix((np.ones(len(e)),e.T),shape=(len(unique),len(unique))).tocsr()
    graph=(graph+graph.T).astype(bool)
    count,labels=connected_components(graph,directed=False)
    body=original[cargo_faces]+shift
    index=cKDTree(body.mean(1))
    def surface(q):
        t=body[index.query(q,k=96)[1]];p=closest_point(t,np.tile(q,(len(t),1)))
        return p[np.linalg.norm(p-q,axis=1).argmin()]
    target=fit.copy();anchors=[]
    for label in range(count):
        ids=np.flatnonzero(labels==label);raw=np.flatnonzero(labels[inv]==label)
        if weights[raw].max()<.9:continue
        caps=ids[np.diff(graph[ids][:,ids].indptr)>=10]
        if len(caps)!=2:raise RuntimeError("Unexpected mixed-mask strap topology")
        closest=np.linalg.norm(source[raw,None]-unique[caps][None,:],axis=2).argmin(1)
        for side,cap in enumerate(caps):
            original_cap=unique[cap]
            position=original_cap+shift
            hit=surface(position)
            toward=hit-position
            goal=hit+.06*toward/max(1e-8,np.linalg.norm(toward))
            ix=raw[closest==side]
            target[ix]=fit[ix]+(source[ix]+goal-original_cap-fit[ix])*weights[ix,None]
            anchors.append((np.flatnonzero(inv==cap),goal))
    rebuilt,stats=repair(source,target,sf,weights)
    t=np.clip(weights/.16,0,1);t=t*t*(3-2*t)
    final=fit+(rebuilt-fit)*t[:,None]
    for ids,goal in anchors:
        center=final[ids].mean(0);k=np.clip(1-np.linalg.norm(final-center,axis=1)/2.8,0,1)
        final+=(goal-center)*(k*k*(3-2*k)*weights)[:,None]
    gaps=[np.linalg.norm(surface(final[ids].mean(0))-final[ids].mean(0)) for ids,_ in anchors]
    return keep,final,gaps,stats


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    plan=read(CURRENT/"authored.json");caps=read(CURRENT/"captured.json")
    result=[];routes=[];details=[];sling={}
    adjustments=read(OUT/"adjustments.json") if (OUT/"adjustments.json").exists() else {}
    for row in plan["rows"]:
        rig,item=row["rig"],row["item"]
        if row.get("rigid_mesh") and item!="ue_simple_sling_bag":continue
        native,_,cap=derive(row,"rows")
        p,f=geometry(cap);current=coords(row["positions"])
        if not np.array_equal(f,geometry(caps[row["source"]])[1]):raise RuntimeError("Native strip vertex order changed")
        if item=="ue_simple_sling_bag":
            sling[rig]=dict(pouch=row["rigid_mesh"],immutable_pouch="/SimpleSlingBag20261022/SM_SimpleSlingPouch." in row["rigid_mesh"],
                strap_longest_source_cm=edges(p,f).max(),strap_longest_current_cm=edges(current,f).max(),gravity=row.get("hanging_pack") is not None)
            continue
        cargo=np.fromfile(cap["cargo_vertices"],"u1").astype(bool)
        mask=np.fromfile(Path(cap["folder"])/"mask.bin","<f4")
        cf=f[cargo[f].all(1)]
        if np.any(cargo[f].any(1)!=cargo[f].all(1)):raise RuntimeError("Cargo islands unexpectedly connected to strap islands")
        delta=safe_shift(rig,p,cf)
        delta[1]-=adjustments.get(rig+"/"+item,0.)
        new=p+delta
        ix,strap,gaps,stats=straps(p,current,f,mask,cargo,delta,cf)
        new[ix]=strap
        edge=edges(p,cf);error=np.max(np.abs(edges(new,cf)-edge))
        if not gaps or max(gaps)>.22 or error>.00001:raise RuntimeError(f"Cargo or seam failed {rig}/{item}: {gaps}, {error}")
        label=f"SK_{rig}_{item.removeprefix('ue_')}_TS01";asset=f"{DEST}/{rig}/{label}"
        file=OUT/(label+".bin");new.astype("<f4").tofile(file)
        result.append(dict(asset=asset,source=native["source"],source_sha256=cap["package_sha256"],positions=str(file),vertices=len(new)))
        support=dict(row["support"]);support.update(bounds_min=new[cargo].min(0).tolist(),bounds_max=new[cargo].max(0).tolist())
        # The chosen soft cargo transform is a translation of its native donor.
        # Its dynamics pivot follows that native cargo by the identical amount.
        native_recipe=read(derive(row,"rows")[1]/"plan.json")
        origin=next(q for q in native_recipe["rows"] if (q["rig"],q["shirt"],q["item"])==(rig,native["shirt"],item))
        motion=origin["outfit"]["backpack_motion"];base=motion.get("support_by_shirt",{}).get(native["shirt"]) or motion.get("support") or motion
        support["pivot"]=(np.asarray(base["pivot"])+delta).tolist()
        routes.append(dict(rig=rig,item=item,shirt=row["shirt"],mesh=asset,support=support,bounds_min=new.min(0).tolist(),bounds_max=new.max(0).tolist()))
        details.append(dict(rig=rig,item=item,source_directory=cap["folder"],source=native["source"],cargo_vertices=cap["cargo_vertices"],
                            translation_cm=delta.tolist(),source_cargo_longest_edge_cm=edge.max(),prior_cargo_longest_edge_cm=edges(current,cf).max(),
                            final_cargo_longest_edge_cm=edges(new,cf).max(),max_edge_length_error_cm=error,seam_gaps_cm=gaps,
                            retained_shoulder_points=int(((~cargo)&(mask==0)).sum()),sections=stats))
        print(rig,item,"shift",delta,"seams",np.round(gaps,3),"longest",round(edge.max(),2),flush=True)
    write("staged.json",dict(rows=result,statics=[]));write("routes.json",routes);write("sources.json",details);write("sling.json",sling)


if __name__=="__main__":main()
