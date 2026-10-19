"""Requested offline sleeve comparison against the current native arms."""
import json
from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial import cKDTree
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/GarmentSleeveRepair20261018'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def side_weights(weights):return np.array([0 if sum(v for n,v in w.items() if n.endswith('_l'))>=sum(v for n,v in w.items() if n.endswith('_r')) else 1 for w in weights])
def topology(d):
    p=np.array(d['positions']);f=np.array(d['triangles']);_,first,remap=np.unique(np.round(p,5),axis=0,return_index=True,return_inverse=True);wf=remap[f];edges=np.sort(np.concatenate((wf[:,[0,1]],wf[:,[1,2]],wf[:,[2,0]])),axis=1);ue,c=np.unique(edges,axis=0,return_counts=True);ep=p[first][ue[c==1]]
    return dict(vertices=len(p),triangles=len(f),open_edges=int(sum(c==1)),nonmanifold_edges=int(sum(c>2)),duplicate_faces=int(len(f)-len(np.unique(np.sort(wf,axis=1),axis=0))),max_edge_cm=float(np.linalg.norm(p[f]-p[np.roll(f,1,axis=1)],axis=2).max()),open_edge_bounds=[ep.min((0,1)).tolist(),ep.max((0,1)).tolist()] if len(ep) else None)
def native_clearance(d,skin):
    p=np.array(d['positions']);f=np.array(d['triangles']);m=np.array(d['triangle_materials']);sp=np.array(skin['positions']);sf=np.array(skin['triangles']);ss=side_weights(skin['weights']);side=side_weights(d['weights']);report={}
    for k,suffix in enumerate(('l','r')):
        ids=np.where(side==k)[0]
        if len(ids)<10:continue
        b=skin['bones'];a,e,w=[np.array(b[n+'_'+suffix]['position']) for n in ('upperarm','lowerarm','hand')];upper=(e-a)/np.linalg.norm(e-a);lower=(w-e)/np.linalg.norm(w-e)
        prox=-(p-w)@lower;shoulder=(p-a)@upper
        # Sample cloth shell/lining only. Metal torus detail is a separate part.
        bymat={}
        for mat in sorted(set(m)):
            chosen=np.unique(f[m==mat]);chosen=chosen[(side[chosen]==k)&(shoulder[chosen]>3)&(prox[chosen]>.8)]
            if not len(chosen):continue
            faces=sf[np.all(ss[sf]==k,axis=1)];tris=sp[faces];tree=cKDTree(tris.mean(1));distances=[];normalgaps=[]
            for start in range(0,len(chosen),500):
                query=p[chosen[start:start+500]];_,near=tree.query(query,k=24);candidate=tris[near];q=trimesh.triangles.closest_point(candidate.reshape(-1,3,3),np.repeat(query,24,axis=0)).reshape(-1,24,3);distance=np.linalg.norm(q-query[:,None,:],axis=2);best=distance.argmin(1);actual=candidate[np.arange(len(query)),best];normal=-np.cross(actual[:,1]-actual[:,0],actual[:,2]-actual[:,0]);normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-12);gap=np.einsum('ij,ij->i',query-q[np.arange(len(query)),best],normal);normalgaps.extend(gap.tolist());distances.extend(distance[np.arange(len(query)),best].tolist())
            g=np.array(normalgaps);distance=np.array(distances)
            # Native arms have open shoulder/skin-section boundaries. A signed
            # plane distance is not penetration when the closest point lies far
            # off the normal projection, outside that finite triangle.
            projected=np.abs(g)>=distance*.98
            valid=g[projected]
            bymat[str(mat)]=dict(samples=len(g),normal_projection_samples=int(sum(projected)),gap_cm=np.percentile(g,[0,1,10,50,90,99,100]).round(4).tolist(),projected_gap_cm=np.percentile(valid,[0,1,10,50,90,99,100]).round(4).tolist() if len(valid) else [],inside_over_1mm=int(sum((g<-.1)&projected)))
        report[suffix]=dict(wrist_nearest_cm=float(prox[ids].min()),cuff_from_shoulder_max_cm=float(shoulder[ids].max()),materials=bymat)
    return report
def main():
    inventory=read(R/'inventory.json');results=[]
    for row in inventory['rows']:
        d=read(row['file']);skin=read(row['native_file']);entry=dict(item=row['item'],profile=row['profile'],asset=row['asset'],topology=topology(d),clearance=native_clearance(d,skin),lod_count=d['lod_count'],lod_policy=d['lod_policy'],materials=d['materials'],colors_present=bool(d['colors']))
        results.append(entry);print(row['item'],row['profile'],'open',entry['topology']['open_edges'],'nonmanifold',entry['topology']['nonmanifold_edges'],'duplicates',entry['topology']['duplicate_faces'],'clearance',[(s,{m:x['inside_over_1mm'] for m,x in v['materials'].items()}) for s,v in entry['clearance'].items()],flush=True)
        (R/'diagnosis.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print('GARMENT_SOURCE_INSPECTION_COMPLETE',len(results),flush=True)
if __name__=='__main__':main()
