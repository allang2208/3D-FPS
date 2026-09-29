import json
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ShortSleeveTraversalFix20260929';OLD=P/'SourceAssets/ShortSleeveTraversalDiagnosis20260929'
shirt=json.loads((OLD/'shirt.json').read_text());skin=json.loads((OLD/'skin.json').read_text());q=np.array(skin['positions']);trees={}
for side in ['l','r']:
 faces=[f for f,m in zip(skin['triangles'],skin['materials']) if m==0 and all(q[i,0]<0 if side=='l' else q[i,0]>0 for i in f)]
 trees[side]=(BVHTree.FromPolygons([Vector(v) for v in q],faces,all_triangles=True),faces)
edits=[]
for i,p in enumerate(shirt['positions']):
 side='l' if p[0]<0 else 'r';tree,faces=trees[side];hit,normal,fi,distance=tree.find_nearest(Vector(p))
 if fi is None or distance>10:raise RuntimeError('No corresponding upperarm '+str(i))
 ids=faces[fi];a,b,c=q[ids];v0=b-a;v1=c-a;v2=np.array(hit)-a;den=(v0@v0)*(v1@v1)-(v0@v1)**2
 if abs(den)<1e-12:raise RuntimeError('Degenerate source')
 v=((v1@v1)*(v2@v0)-(v0@v1)*(v2@v1))/den;w=((v0@v0)*(v2@v1)-(v0@v1)*(v2@v0))/den;bary=np.maximum([1-v-w,v,w],0);bary/=sum(bary);weights={}
 for vi,mix in zip(ids,bary):
  for n,value in skin['weights'][vi].items():weights[n]=weights.get(n,0)+float(mix*value)
 weights=dict(sorted(((n,v) for n,v in weights.items() if v>1e-6),key=lambda x:-x[1])[:8]);total=sum(weights.values());weights={n:v/total for n,v in weights.items()}
 shirt['weights'][i]=weights;edits.append(dict(vertex_id=i,weights=weights))
(R/'shirt.json').write_text(json.dumps(shirt,separators=(',',':')));(R/'edits.json').write_text(json.dumps(edits,separators=(',',':')))
(R/'skin.json').write_bytes((OLD/'skin.json').read_bytes())
print('TRAVERSAL_SHORT_SLEEVE_FIT',len(edits),flush=True)
