"""Read connected source surfaces for the requested M27 rebinding work."""
from pathlib import Path
import json
import numpy as np
import bpy

BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27')
OUT=BASE/'BindingV2'; OUT.mkdir(exist_ok=True)
d=np.load(BASE/'ProductionV1/source_geometry.npz')
p=d['positions']; triangles=d['indices']
points,first,inverse=np.unique(np.round(p,6),axis=0,return_index=True,return_inverse=True)
faces=inverse[triangles]
edges=np.unique(np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1),axis=0)
adj=[[] for _ in points]
for a,b in edges: adj[a].append(int(b)); adj[b].append(int(a))
def components(mask):
    labels=np.full(len(points),-1,dtype=np.int32); groups=[]
    for start in np.flatnonzero(mask):
        if labels[start]>=0:continue
        label=len(groups); stack=[int(start)]; labels[start]=label; ids=[]
        while stack:
            v=stack.pop(); ids.append(v)
            for nxt in adj[v]:
                if mask[nxt] and labels[nxt]<0:labels[nxt]=label;stack.append(nxt)
        groups.append(np.asarray(ids,dtype=np.int32))
    return labels,groups
labels,groups=components(np.ones(len(points),bool))
def describe(ids):
    q=points[ids]
    return dict(vertices=len(ids),minimum=q.min(axis=0).round(5).tolist(),maximum=q.max(axis=0).round(5).tolist(),center=q.mean(axis=0).round(5).tolist())
record={'components':[describe(g) for g in sorted(groups,key=len,reverse=True)[:35]],'cross_sections':{}}
for name,mask in [('below_elbows',points[:,1]<.22),('below_ankles',points[:,1]<-.75)]+[('below_'+str(v),points[:,1]<v) for v in [.30,.40,.50,.60]]:
    _,parts=components(mask)
    record['cross_sections'][name]=[describe(g) for g in sorted(parts,key=len,reverse=True)[:5]]
record['right_limb_sections']=[]
for height in [-.92,-.84,-.76,-.60,-.36,0,.20,.31,.43,.55,.62]:
    mask=(np.abs(points[:,1]-height)<.009)&(points[:,0]>.10)
    _,parts=components(mask)
    record['right_limb_sections'].append({'y':height,'parts':[describe(g) for g in sorted(parts,key=len,reverse=True)[:5]]})
np.savez_compressed(OUT/'connected_source.npz',points=points,first=first,inverse=inverse,faces=faces,edges=edges,component=labels)
(OUT/'source_regions.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps({'cross_sections':record['cross_sections'],'right_limb_sections':record['right_limb_sections']}),flush=True)
