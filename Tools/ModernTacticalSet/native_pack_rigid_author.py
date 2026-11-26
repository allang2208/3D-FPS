"""Fit unchanged native rigid cargo to the equipped TS01 shirt and reseat its six sewn strap ends."""
from functools import lru_cache
import json
from pathlib import Path
import sys

import numpy as np
from scipy.interpolate import RegularGridInterpolator
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation
from trimesh.triangles import closest_point

P=Path(__file__).resolve().parents[2]
BASE=P/"SourceAssets/BackpackFit20261024"
CURRENT=BASE/"ModernTacticalShoulders20261118"
REV="ModernTacticalNativePacks20261118"
OUT=BASE/REV/"Rigid"
DEST="/Game/Characters/BackpackFit20261024/"+REV
sys.path.insert(0,str(P/"Tools/BackpackFit"))
from preserve_sections import repair


@lru_cache(None)
def read(file):
    return json.loads(file.read_bytes())


def write(name,data):
    (OUT/name).write_text(json.dumps(data,indent=2),encoding="utf-8")


def coords(file):
    return np.fromfile(file,dtype="<f4").reshape(-1,3).astype(float)


def derive(row,kind):
    revision=CURRENT
    while row["source"].startswith("/Game/Characters/BackpackFit20261024/"):
        asset=row["source"].split(".")[0]
        revision=BASE/asset.split("/")[4]
        row=next(q for q in read(revision/"authored.json")[kind] if q["asset"]==asset)
    return row,revision,read(revision/"captured.json")[row["source"]]


def geometry(record):
    folder=Path(record["folder"])
    return coords(folder/"positions.bin"),np.fromfile(folder/"triangles.bin",dtype="<i4").reshape(-1,3)


def choose_location(rig,row,native_row,local,faces):
    loc=np.array(row["rigid_location"]).copy()
    # Start from the original upright wearable and change only fore/aft clearance.
    loc[1]=native_row["rigid_location"][1]
    rotation=Rotation.from_quat(row["rigid_rotation_quat"]).as_matrix()
    frame=read(CURRENT/"Surfaces/frames.json")[rig]
    transform=np.asarray(frame["matrix"])
    field=np.load(CURRENT/"Surfaces"/(rig+"_ue_modern_kevlar_vest.npz"))
    rear=RegularGridInterpolator((field["xs"],field["zs"]),field["guarded_rear"],bounds_error=False,fill_value=np.nan)
    samples=np.concatenate([local,local[faces].mean(axis=1)])
    def gaps():
        world=samples@rotation.T+loc
        reference=(world-frame["translation"])@transform.T
        return rear(reference[:,[0,2]])-reference[:,1]
    gap=gaps()
    for _ in range(4):
        shift=.40-float(np.nanmin(gap))
        if shift<=.005:break
        loc[1]-=shift/max(.94,transform[1,1])
        gap=gaps()
    return loc,rotation,float(np.nanmin(gap))


def fit_harness(native,current,faces,mask,reference_location,reference_rotation,location,rotation,local,body_faces):
    # The native three ribbons have two cap-centre nodes each. Place their
    # physical endpoints against the real original shell, then rebuild the free
    # part of each ribbon while pinning its existing fitted shoulder contact.
    unique,inverse=np.unique(np.round(native,4),axis=0,return_inverse=True)
    weight=np.bincount(inverse,weights=mask)/np.bincount(inverse)
    fc=inverse[faces]
    e=np.concatenate([fc[:,[0,1]],fc[:,[1,2]],fc[:,[2,0]]])
    graph=coo_matrix((np.ones(len(e)),e.T),shape=(len(unique),len(unique))).tocsr()
    graph=(graph+graph.T).astype(bool)
    count,labels=connected_components(graph,directed=False)
    cargo=local@rotation.T+location
    nearest=cKDTree(cargo[body_faces].mean(axis=1))
    result=current.copy()
    deltas=np.zeros_like(native)
    anchors=[]
    def surface(q):
        adjacent=nearest.query(q,k=96)[1]
        pts=closest_point(cargo[body_faces[adjacent]],np.tile(q,(len(adjacent),1)))
        return pts[np.linalg.norm(pts-q,axis=1).argmin()]
    for label in range(count):
        ids=np.flatnonzero(labels==label)
        if weight[ids].max()<.9:continue
        caps=ids[np.diff(graph[ids][:,ids].indptr)>=10]
        if len(caps)!=2 or not np.all(weight[caps]>.99):
            raise RuntimeError("Unsupported sewn strap topology")
        raw=np.flatnonzero(labels[inverse]==label)
        distances=np.linalg.norm(native[raw,None]-unique[caps][None,:],axis=2)
        for j,c in enumerate(caps):
            cap=unique[c];fixed=(cap-reference_location)@reference_rotation@rotation.T+location
            contact=surface(fixed)
            towards=contact-fixed
            end=contact+.08*towards/max(.001,np.linalg.norm(towards))
            members=raw[distances.argmin(axis=1)==j]
            moved=(native[members]-cap)@reference_rotation@rotation.T+end
            deltas[members]=moved-current[members]
            anchors.append((np.flatnonzero(inverse==c),end,surface))
    if len(anchors)!=6:raise RuntimeError("Expected six cargo-side sewn endpoints")
    weight=mask[:,None]
    target=current+deltas*weight
    reconstructed,stats=repair(native,target,faces,mask)
    blend=np.clip(weight/.16,0,1)
    blend=blend*blend*(3-2*blend)
    result=current+(reconstructed-current)*blend
    # Section reconstruction can slightly recenter a rounded end cap; seat
    # that last half-centimetre together with its adjoining tube section.
    for ids,end,_ in anchors:
        center=result[ids].mean(axis=0)
        influence=np.clip(1-np.linalg.norm(result-center,axis=1)/2.8,0,1)
        result+=(end-center)*(influence*influence*(3-2*influence)*mask)[:,None]
    gaps=[np.linalg.norm(surface(result[ids].mean(0))-result[ids].mean(0)) for ids,_,surface in anchors]
    return result,stats,gaps


def record(captured,source,asset,points):
    file=OUT/(asset.split("/")[-1]+".bin")
    points.astype("<f4").tofile(file)
    return dict(source=source,source_sha256=captured["package_sha256"],asset=asset,positions=str(file),vertices=len(points))


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    current=read(CURRENT/"authored.json")
    current_statics={r["asset"]:r for r in current["statics"]}
    current_caps=read(CURRENT/"captured.json")
    rows=[];statics=[];routes=[];report=[]
    for row in current["rows"]:
        rig,item=row["rig"],row["item"]
        if item not in ("ue_pathfinder_backpack","ue_farreach_backpack","ue_special_duty_backpack"):continue
        label=item.removeprefix("ue_")
        harness,version,hcap=derive(row,"rows")
        shell,_,scap=derive(current_statics[row["rigid_mesh"].split(".")[0]],"statics")
        native_config=next(q for q in read(version/"plan.json")["rows"] if (q["rig"],q["item"],q["shirt"])==(rig,item,harness["shirt"]))
        orig,f=geometry(hcap);local,sf=geometry(scap)
        if not np.array_equal(f,geometry(current_caps[row["source"]])[1]):
            raise RuntimeError("Current and original strap topology differ")
        location,rotation,gap=choose_location(rig,row,native_config,local,sf)
        extra_file=OUT/"helmet-adjustments.json"
        if extra_file.exists():location[1]-=read(extra_file).get(rig+"/"+item,0.)
        native_loc=np.array(native_config["rigid_location"])
        native_rot=Rotation.from_quat(native_config["rigid_rotation_quat"]).as_matrix()
        mask=np.fromfile(Path(hcap["folder"])/"mask.bin",dtype="<f4")
        existing=coords(row["positions"])
        new,stats,anchors=fit_harness(orig,existing,f,mask,native_loc,native_rot,location,rotation,local,sf)
        rigid=local@rotation.T+location
        sk=record(hcap,harness["source"],f"{DEST}/{rig}/SK_{rig}_{label}_TS01",new)
        sm=record(scap,shell["source"],f"{DEST}/{rig}/SM_{rig}_{label}_TS01",local)
        rows.append(sk);statics.append(sm)
        both=np.vstack([new,rigid])
        pivot=np.asarray(row["support"]["pivot"])+location-np.asarray(row["rigid_location"])
        routes.append(dict(rig=rig,item=item,shirt=row["shirt"],mesh=sk["asset"],rigid=sm["asset"],
                           rigid_location=location.tolist(),rigid_rotation_quat=row["rigid_rotation_quat"],
                           bounds_min=both.min(0).tolist(),bounds_max=both.max(0).tolist(),
                           support=dict(pivot=pivot.tolist(),bounds_min=rigid.min(0).tolist(),bounds_max=rigid.max(0).tolist())))
        edge=np.linalg.norm(local[sf]-np.roll(local[sf],1,axis=1),axis=2).max()
        shell_binary_identical=(Path(scap["folder"])/"positions.bin").read_bytes()==Path(sm["positions"]).read_bytes()
        if not shell_binary_identical or max(anchors)>.20:
            raise RuntimeError("The cargo geometry or harness ends did not meet the requested fit")
        report.append(dict(rig=rig,item=item,source_shell=shell["source"],source_shell_directory=scap["folder"],
                           source_harness=harness["source"],source_harness_directory=hcap["folder"],
                           rigid_vertices_byte_identical=shell_binary_identical,source_and_final_longest_edge_cm=float(edge),
                           rear_field_min_clearance_cm=gap,original_anchor_location=native_loc.tolist(),
                           torso_fixed_vertices=int((mask==0).sum()),fixed_vertices_peak_delta_cm=float(np.linalg.norm(new[mask==0]-existing[mask==0],axis=1).max()),
                           seam_end_nearest_shell_cm=list(anchors),strip_reconstruction=stats))
        print(rig,item,"nearest sewn ends, cm",np.round(anchors,3),"shell longest edge",round(edge,3),flush=True)
    write("staged.json",dict(rows=rows,statics=statics))
    write("routes.json",routes);write("original-sources.json",report)


if __name__=="__main__":
    main()
