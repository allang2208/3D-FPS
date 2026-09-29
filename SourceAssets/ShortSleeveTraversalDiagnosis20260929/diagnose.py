"""Read-only offline skinning and upper-arm surface intersection diagnosis."""
import json
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector,Matrix,Quaternion
from mathutils.bvhtree import BVHTree
R=Path('D:/FPS3D/FPSGAME/SourceAssets/ShortSleeveTraversalDiagnosis20260929')
def read(p):return json.loads(p.read_text())
def matrix(t):return np.asarray(Matrix.Translation(Vector(t['p']))@Quaternion((t['q'][3],*t['q'][:3])).to_matrix().to_4x4()@Matrix.Diagonal(Vector((*t['s'],1))))
shirt=read(R/'shirt.json');skin=read(R/'skin.json')
def posed(d,pose):
 p=np.asarray(d['positions']);out=np.zeros_like(p);sums=np.zeros(len(p));groups={}
 for i,w in enumerate(d['weights']):
  for n,v in w.items():groups.setdefault(n,[]).append((i,v))
 for n,rows in groups.items():
  if n not in pose:raise RuntimeError('Missing animated bone '+n)
  m=matrix(pose[n])@np.linalg.inv(matrix(d['rest'][n]));ids=np.array([r[0] for r in rows]);w=np.array([r[1] for r in rows]);out[ids]+=(p[ids]@m[:3,:3].T+m[:3,3])*w[:,None];sums[ids]+=w
 return out/np.maximum(sums[:,None],1e-9)
# Exclude shoulder caps and inner lining; count only outer cloth intersecting
# skin in the exposed upper-arm neighbourhood, away from the open shoulder end.
selected={}
for name,d in [('shirt',shirt),('skin',skin)]:
 p=np.array(d['positions']);faces=np.array(d['triangles']);mid=p[faces].mean(1);keep=[]
 for fi,(f,m) in enumerate(zip(faces,d['materials'])):
  if m!=0:continue
  side='l' if mid[fi,0]<0 else 'r';w=np.array(d['rest']['upperarm_'+side]['p']);el=np.array(d['rest']['lowerarm_'+side]['p']);axis=(el-w)/np.linalg.norm(el-w);q=mid[fi]-w;t=q@axis
  if not 3<t<19:continue
  if name=='shirt':
   normal=-np.cross(p[f[1]]-p[f[0]],p[f[2]]-p[f[0]])
   if normal@(q-axis*t)<=0:continue
  keep.append(fi)
 selected[name]=keep
base=np.array(shirt['positions']);f=np.array(shirt['triangles'])[selected['shirt']];edges=np.unique(np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1),axis=0);length=np.linalg.norm(base[edges[:,0]]-base[edges[:,1]],axis=1);valid=length>.05;edges=edges[valid];length=length[valid]
rows=[]
for key,pose in [('rest',skin['rest'])]+list(skin['poses'].items()):
 ps=posed(shirt,pose);pb=posed(skin,pose)
 sf=[shirt['triangles'][i] for i in selected['shirt']];bf=[skin['triangles'][i] for i in selected['skin']]
 a=BVHTree.FromPolygons([Vector(v) for v in ps],sf,all_triangles=True);b=BVHTree.FromPolygons([Vector(v) for v in pb],bf,all_triangles=True);overlap=a.overlap(b)
 ratio=np.linalg.norm(ps[edges[:,0]]-ps[edges[:,1]],axis=1)/length
 rows.append(dict(pose=key,cloth_intersection_triangles=len({i for i,j in overlap}),intersection_pairs=len(overlap),max_edge_stretch=float(ratio.max()),p95_edge_stretch=float(np.percentile(ratio,95))))
print(json.dumps(rows,indent=2),flush=True)
weights=[sum(v for n,v in w.items() if n.startswith('spine_')) for w in shirt['weights']]
report=dict(method='Saved compressed clips sampled offline, LOD0, no contact IK or runtime camera; outer-shirt/upper-arm triangle intersection and edge stretch',samples=rows,maximum_shirt_spine_weight=max(weights),vertices_with_spine_weight=sum(v>.1 for v in weights),assets_modified=False)
(R/'report.json').write_text(json.dumps(report,indent=2))
