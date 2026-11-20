"""Seat the TS01 rigid pack bodies and sewn ribbon ends against the complete reference helmet."""
import json
import math
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

from native_pack_publish import P,R,SHIRT,CONFIG,fields,get,key,read,record,root,sha


F=R/"ExfilR4"
REVIEW=P/"SourceAssets/ModernTacticalSet20261113/ExfilReferenceR4/Review"


def seam_centres(donor,points,mask):
    native=np.fromfile(donor/"positions.bin","<f4").reshape(-1,3)
    faces=np.fromfile(donor/"triangles.bin","<i4").reshape(-1,3)
    weld,inv=np.unique(np.round(native.astype(float),4),axis=0,return_inverse=True)
    tri=inv[faces]
    e=np.concatenate((tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]))
    graph=coo_matrix((np.ones(len(e)),e.T),shape=(len(weld),len(weld))).tocsr()
    graph=(graph+graph.T).astype(bool)
    n,labels=connected_components(graph,directed=False)
    weights=np.bincount(inv,weights=mask)/np.bincount(inv)
    centres=[]
    for i in range(n):
        ids=np.flatnonzero(labels==i)
        if weights[ids].max()<.9:continue
        caps=ids[np.diff(graph[ids][:,ids].indptr)>=10]
        if len(caps)!=2 or weights[caps].min()<.99:raise ValueError("Unexpected sewn end")
        centres.extend([points[inv==cap].mean(0,dtype=float).tolist() for cap in caps])
    if len(centres)!=6:raise ValueError("Unexpected rigid harness topology")
    return centres


def capture():
    evidence=read(REVIEW/"backpack-clearance.json")
    source=read(R/"authored.json")
    routes=read(R/"Rigid/routes.json")
    deps=read(R/"Rigid/original-sources.json")
    config=read(CONFIG)
    result={}
    for name in evidence["overlapping_combinations"]:
        rig,item=name.split("/")
        row=next(r for r in routes if key(r)==name)
        entry=next(e for e in source["rows"] if e["asset"]==row["mesh"])
        body=next(e for e in source["statics"] if e["asset"]==row["rigid"])
        donor=next(e for e in deps if key(e)==name)
        geometry=evidence["combinations"][name]["components"]
        limit=max(part.get("minimum_sampled_rigid_translation_rearward_cm",0.) for part in geometry.values())
        if not limit or any(part["intersections"] for k,part in geometry.items() if not k.startswith("rigid_mesh/")):
            raise RuntimeError("Expected a cargo-only intersection for "+name)
        fields_before={"/".join(path):get(get(config,root(row)),path) for path in fields(row)}
        result[name]=dict(route=row,entry=entry,body=body,donor=donor,fields_before=fields_before,
                          rearward_cm=math.ceil((limit+.15)*100)/100,
                          source_sha256=sha(Path(entry["positions"])),minimum_sampled_cm=limit)
    if len(result)!=4:raise RuntimeError("Unexpected affected cargo count")
    record(F/"prior.json",result)


def author():
    F.mkdir(exist_ok=True)
    if not (F/"prior.json").exists():capture()
    prior=read(F/"prior.json")
    active=read(R/"authored.json")
    contact=read(R/"Contact/author.json")
    rigid_files=(R/"Rigid/author.json",R/"Rigid/staged.json")
    baselines=[read(path) for path in rigid_files]
    routes=read(R/"Rigid/routes.json")
    before=read(R/"before-routes.json")
    metrics={}
    for name,case in prior.items():
        row=case["route"];entry=case["entry"];delta=case["rearward_cm"]
        donor=Path(case["donor"]["source_harness_directory"])
        original=Path(entry["positions"])
        if sha(original)!=case["source_sha256"]:raise RuntimeError("Harness source changed: "+name)
        positions=np.fromfile(original,"<f4").reshape(-1,3)
        mask=np.fromfile(donor/"mask.bin","<f4")
        # The attached ends move rigidly with the cargo. Only the free ribbon
        # length stretches between its pinned shoulder contact and sewn ends.
        t=np.clip((mask-.12)/(.95-.12),0.,1.)
        influence=t*t*(3.-2.*t)
        step=np.array([0.,-delta,0.])
        fitted=(positions+step*influence[:,None]).astype("<f4")
        new=dict(entry,asset=entry["asset"]+"_EXFIL")
        file=F/(new["asset"].rsplit("/",1)[-1]+".bin")
        fitted.tofile(file);new["positions"]=str(file)
        for manifest in (active,contact):
            idx=next(i for i,q in enumerate(manifest["rows"]) if q["asset"] in (entry["asset"],new["asset"]))
            manifest["rows"][idx]=new
        for manifest in baselines:
            baseline=next(q for q in manifest["rows"] if q["asset"] in (entry["asset"],new["asset"]))
            baseline["asset"]=new["asset"]
        updated=dict(row,mesh=new["asset"],rigid_location=(np.array(row["rigid_location"])+step).tolist(),
                     support={k:(np.array(v)+step).tolist() for k,v in row["support"].items()})
        shell=np.fromfile(case["body"]["positions"],"<f4").reshape(-1,3)
        rot=Rotation.from_quat(row["rigid_rotation_quat"]).as_matrix()
        combined=np.vstack([fitted,shell@rot.T+updated["rigid_location"]])
        updated["bounds_min"]=combined.min(0).tolist();updated["bounds_max"]=combined.max(0).tolist()
        routes[next(i for i,r in enumerate(routes) if key(r)==name)]=updated
        before[name]=case["fields_before"]
        actual=fitted.astype(float)-positions
        metrics[name]=dict(rearward_cm=delta,minimum_sampled_rigid_translation_cm=case["minimum_sampled_cm"],
                           authored_sewn_cap_centres=seam_centres(donor,fitted,mask),
                           fixed_shoulder_vertices=int((t==0).sum()),max_fixed_displacement_cm=float(np.max(np.linalg.norm(actual[t==0],axis=1))),
                           max_attached_end_translation_error_cm=float(np.max(np.linalg.norm(actual[t==1]-step,axis=1))),
                           original_max_six_seam_ends_cm=max(case["donor"]["seam_end_nearest_shell_cm"]),
                           rigid_package_unchanged=case["body"]["asset"])
    record(R/"authored.json",active);record(R/"Contact/author.json",contact)
    for path,baseline in zip(rigid_files,baselines):record(path,baseline)
    record(R/"Rigid/routes.json",routes);record(R/"before-routes.json",before)
    record(F/"seam-fit.json",metrics)


if __name__=="__main__":author()
