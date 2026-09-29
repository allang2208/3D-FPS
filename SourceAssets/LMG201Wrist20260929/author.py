"""Fit the 201 left wrist to its visible glove skin; retain ADS34 right sleeve."""
import json
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/LMG201Wrist20260929'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
shirt=read(R/'shirt.json');skin=read(R/'skin.json');p=np.array(shirt['positions']);q=np.array(skin['positions']);w=np.array(shirt['bones']['hand_l']['position']);e=np.array(shirt['bones']['lowerarm_l']['position']);axis=(w-e)/np.linalg.norm(w-e)
t=(p-w)@axis;st=(q-w)@axis
faces=[f for f,m in zip(skin['triangles'],skin['triangle_materials']) if m in [1,2,4] and all(q[i,0]<0 and -19<st[i]<1 for i in f)]
tree=BVHTree.FromPolygons([Vector(v) for v in q],faces,all_triangles=True)
old=read(P/'SourceAssets/ChainmailInterlace20260929/Authored/PKM.json');new=read(P/'SourceAssets/ChainmailInsetBinding20260929/Authored/PKM.json')
oldp=np.array(old['positions']);newp=np.array(new['positions']);kdt=KDTree(len(oldp))
for index,value in enumerate(oldp):kdt.insert(Vector(value),index)
kdt.balance()
edits=[];maximum=0.;distances=[]
for i,point in enumerate(p):
 if point[0]>=0 or t[i]<=-16:continue
 hit,normal,fi,distance=tree.find_nearest(Vector(point))
 if fi is None or distance>5:raise RuntimeError('Left wrist skin correspondence '+str(i))
 ids=faces[fi];a,b,c=q[ids];v0=b-a;v1=c-a;v2=np.array(hit)-a;den=(v0@v0)*(v1@v1)-(v0@v1)**2
 if abs(den)<1e-12:continue
 v=((v1@v1)*(v2@v0)-(v0@v1)*(v2@v1))/den;z=((v0@v0)*(v2@v1)-(v0@v1)*(v2@v0))/den
 bary=np.maximum([1-v-z,v,z],0);bary/=sum(bary);target={}
 for vi,mix in zip(ids,bary):
  for name,value in skin['weights'][vi].items():target[name]=target.get(name,0)+float(mix*value)
 alpha=float(np.clip((t[i]+16)/7,0,1));alpha=alpha*alpha*(3-2*alpha);before=shirt['weights'][i]
 result={n:before.get(n,0)*(1-alpha)+target.get(n,0)*alpha for n in before.keys()|target.keys()};result=dict(sorted(((n,v) for n,v in result.items() if v>1e-6),key=lambda x:-x[1])[:8]);total=sum(result.values());result={n:v/total for n,v in result.items()}
 delta=sum(abs(result.get(n,0)-before.get(n,0)) for n in result.keys()|before.keys());maximum=max(maximum,delta)
 pos=point;_,j,d=kdt.find(Vector(point))
 if d<.0001:pos=point+newp[j]-oldp[j]
 if delta>1e-6 or np.linalg.norm(pos-point)>1e-6:edits.append(dict(vertex_id=i,weights=result,position=pos.tolist()))
 distances.append(distance)
(R/'edits.json').write_text(json.dumps(edits,separators=(',',':')))
(R/'production.json').write_text(json.dumps(dict(left_vertices=len(edits),maximum_weight_l1_change=maximum,maximum_skin_distance_cm=max(distances),right_sleeve_preserved=True,method='Left distal sleeve inherits visible glove-skin weights by same-side barycentric projection with 7 cm proximal blend; left old external dark roll moved to current inset contour',runtime_tested=False),indent=2))
print('201_LEFT_WRIST_AUTHORED',len(edits),'max weight delta',maximum,flush=True)
