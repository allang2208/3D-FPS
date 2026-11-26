"""Seat the fixed harness across the actual YZ shoulder section while keeping its endpoints."""
from pathlib import Path
import json
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components, dijkstra
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"BackpackFit"))
from preserve_sections import rigid_fit
from scipy.ndimage import map_coordinates, maximum_filter, gaussian_filter, distance_transform_edt
P=Path(__file__).resolve().parents[2]
R=P/"SourceAssets/BackpackFit20261024/ModernTacticalNativePacks20261118"
C=R/"Contact"
def read(p):return json.loads(p.read_bytes())
def write(p,data):p.write_text(json.dumps(data,indent=2))

def seat(p,mask,keep,profile,vertical=True):
    xs=profile["xs"];field=profile["radius"];nt=field.shape[1]
    delta=p[:,1:]-profile["origin"][1:]
    radius=np.linalg.norm(delta,axis=1)
    dirs=delta/np.maximum(radius[:,None],.01)
    xi=(p[:,0]-xs[0])/(xs[1]-xs[0]);ti=np.mod(np.arctan2(delta[:,1],delta[:,0]),2*np.pi)*nt/(2*np.pi)
    def sample(grid,x,t):
        return map_coordinates(np.c_[grid[:,-1],grid,grid[:,0]],np.vstack((x,t+1)),order=1,mode="nearest")
    target=sample(field,xi,ti)
    need=target-radius+(.45 if vertical else 1.15)
    valid=keep&(mask<.8)&(xi>1)&(xi<len(xs)-2)
    if vertical:valid&=dirs[:,1]>-.73
    # A slightly coarser common table moves layers of a strap and buckle alike.
    stride=2.;gx=np.rint(xi/stride).astype(int);gt=np.rint(ti/4.).astype(int)%(nt//4)
    table=np.full(((len(xs)+1)//2,nt//4),-np.inf)
    np.maximum.at(table,(gx[valid],gt[valid]),need[valid])
    known=np.isfinite(table)
    if not known.any():return p
    tiled=np.tile(table,(1,3));nearest=distance_transform_edt(~np.isfinite(tiled),return_distances=False,return_indices=True)
    table=tiled[tuple(nearest)][:,nt//4:nt//2]
    table=np.maximum(0.,table)
    table=maximum_filter(table,size=(5,5),mode=("nearest","wrap"))
    table=gaussian_filter(table,(2.0,2.2),mode=("nearest","wrap"))
    amount=np.clip(sample(table,xi/stride,ti/4.),0.,(4.5+2.*np.clip((np.abs(p[:,0])-8.)/5.,0.,1.)) if vertical else 8.)
    smooth=lambda a:(np.clip(a,0.,1.)**2)*(3-2*np.clip(a,0.,1.))
    amount*=smooth((1.-mask)/.25)*keep
    if vertical:amount*=smooth((dirs[:,1]+.78)/.28)
    new=p.copy();new[:,1:]+=dirs*amount[:,None]
    return new

def preserve_groups(native,before,proposed,faces,keep,mask):
    source,inv=np.unique(np.round(native,4),axis=0,return_inverse=True)
    wf=inv[faces[keep[faces].all(1)]]
    ei=np.concatenate((wf[:,[0,1]],wf[:,[1,2]],wf[:,[2,0]]))
    e=np.unique(np.sort(ei,axis=1),axis=0)
    graph=coo_matrix((np.ones(len(e)),e.T),shape=(len(source),len(source))).tocsr()
    graph=(graph+graph.T).astype(bool)
    _,labels=connected_components(graph,directed=False)
    result=proposed.copy()
    for label in np.unique(labels[inv[keep]]):
        ids=np.flatnonzero(labels==label);raw=np.flatnonzero(labels[inv]==label)
        local=graph[ids][:,ids];caps=np.flatnonzero(np.diff(local.indptr)>=10)
        if len(caps)==2 and len(ids)>=150:
            hops=np.rint(dijkstra(local,directed=False,indices=int(caps[0]),unweighted=True)).astype(int)
            hops[caps[0]]=1;hops[caps[1]]-=1
            stations=hops[np.searchsorted(ids,inv[raw])]
            groups=[raw[stations==i] for i in np.unique(stations)]
        else:groups=[raw]
        for group in groups:
            if len(group)<3 or np.all(mask[group]>.97):continue
            # Each padded cross-section or buckle receives a single rotation.
            result[group]=rigid_fit(before[group],proposed[group])
    result[mask>.97]=before[mask>.97]
    return result

def main():
    summaries={};records=[]
    for family in ("Soft","Rigid"):
        author=read(R/family/"author.json")["rows"]
        sources=read(R/family/("sources.json" if family=="Soft" else "original-sources.json"))
        for a,q in zip(author,sources):
            p=np.fromfile(a["positions"],"<f4").reshape(-1,3).astype(float)
            cap=Path(q.get("source_directory") or q["source_harness_directory"])
            mask=np.fromfile(cap/"mask.bin","<f4");keep=np.ones(len(mask),bool)
            if family=="Soft":keep=~np.fromfile(q["cargo_vertices"],"u1").astype(bool)
            profile=np.load(C/(q["rig"]+".npz"))
            arch=seat(p,mask,keep,profile)
            chest_profile=np.load(C/(q["rig"]+"-chest.npz"))
            chest=seat(p[:,[2,0,1]],mask,keep,chest_profile,False)[:,[1,2,0]]
            t=np.clip((p[:,2]-profile["origin"][2]-10.)/12.,0.,1.)
            t=t*t*(3-2*t)
            target=chest*(1.-t[:,None])+arch*t[:,None]
            native=np.fromfile(cap/"positions.bin","<f4").reshape(-1,3)
            faces=np.fromfile(cap/"triangles.bin","<i4").reshape(-1,3)
            new=preserve_groups(native,p,target,faces,keep,mask)
            path=C/(a["asset"].rsplit("/",1)[-1]+".bin");new.astype("<f4").tofile(path)
            d=np.linalg.norm(new-p,axis=1)
            summaries[q["rig"]+"/"+q["item"]]=dict(maximum_displacement_cm=d.max(),median_fixed_cm=np.median(d[keep&(mask==0)]))
            records.append(dict(a,positions=str(path)))
    write(C/"seating.json",summaries);write(C/"author.json",dict(rows=records,statics=read(R/"Rigid/author.json")["statics"]))
if __name__=="__main__":main()
