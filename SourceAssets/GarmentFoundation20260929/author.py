import json
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path('D:/FPS3D/FPSGAME/SourceAssets/GarmentFoundation20260929')
def read(p):return json.loads(p.read_text())
master=read(R/'ue_chainmail_shirt.json')
def key(d,f):return tuple(sorted(tuple(round(x,4) for x in d['positions'][v]) for v in f))
# Four 52-triangle shoulder closure patches from the original holes_fill output.
caps={key(master,f) for f in master['triangles'][14392:14600]}
assert len(caps)==208
skin=read(R/'bare.json');q=np.array(skin['positions']);trees={}
for side in ['l','r']:
 faces=[f for f,m in zip(skin['triangles'],skin['materials']) if m in [0,1,2,3] and all(q[i,0]<0 if side=='l' else q[i,0]>0 for i in f)]
 trees[side]=(BVHTree.FromPolygons([Vector(v) for v in q],faces,all_triangles=True),faces)
report={}
for name in ['ue_chainmail_shirt','ue_field_sweater','ue_field_sweater_charcoal']:
 d=read(R/(name+'.json'));deleted=[i for i,f in enumerate(d['triangles']) if key(d,f) in caps]
 if len(deleted)!=240:raise RuntimeError('Unexpected shoulder patch topology '+name)
 edits=[]
 if name!='ue_chainmail_shirt':
  for i,p in enumerate(d['positions']):
   tree,faces=trees['l' if p[0]<0 else 'r'];hit,normal,fi,distance=tree.find_nearest(Vector(p));ids=faces[fi];a,b,c=q[ids];v0=b-a;v1=c-a;v2=np.array(hit)-a;den=(v0@v0)*(v1@v1)-(v0@v1)**2
   if abs(den)<1e-12:raise RuntimeError('Degenerate source')
   v=((v1@v1)*(v2@v0)-(v0@v1)*(v2@v1))/den;w=((v0@v0)*(v2@v1)-(v0@v1)*(v2@v0))/den;bary=np.maximum([1-v-w,v,w],0);bary/=sum(bary);weights={}
   for vi,mix in zip(ids,bary):
    for n,value in skin['weights'][vi].items():weights[n]=weights.get(n,0)+float(mix*value)
   weights=dict(sorted(((n,v) for n,v in weights.items() if v>1e-6),key=lambda x:-x[1])[:8]);total=sum(weights.values());weights={n:v/total for n,v in weights.items()};edits.append(dict(vertex_id=i,weights=weights))
 report[name]=dict(source=d['source'],delete_triangles=deleted,weights=edits)
(R/'edits.json').write_text(json.dumps(report,separators=(',',':')))
print({k:len(v['delete_triangles']) for k,v in report.items()},flush=True)
