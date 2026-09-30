"""Read the new Meshy source into a face/loop-preserving authoring archive."""
import bpy,json
import numpy as np
from pathlib import Path
R=Path(__file__).resolve().parent
R.mkdir(exist_ok=True)
S=R.parent/'MeshyRetry28/Meshy/lmg201_new_reference_smooth_v01/downloads/model_urls_glb.glb'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(S))
o=next(o for o in bpy.context.scene.objects if o.type=='MESH')
m=o.data
v=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',v);v=v.reshape(-1,3)
mat=np.array(o.matrix_world);v=v@mat[:3,:3].T+mat[:3,3]
f=np.empty(len(m.loops),np.int32);m.loops.foreach_get('vertex_index',f);f=f.reshape(-1,3)
uv=np.empty(len(m.loops)*2,np.float32);m.uv_layers.active.data.foreach_get('uv',uv);uv=uv.reshape(-1,3,2)
n=np.array([c.vector[:] for c in m.corner_normals],np.float32)@np.linalg.inv(mat[:3,:3]);n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-12)
np.savez_compressed(R/'source_surface.npz',vertices=v,faces=f,uv=uv,normals=n.reshape(-1,3,3))
# Geometry-space connected components help identify isolated artifacts, not parts.
coord,inv=np.unique(np.round(v,7),axis=0,return_inverse=True)
parent=np.arange(len(coord))
def find(i):
 while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
 return i
for tri in inv[f]:
 a=find(tri[0]);b=find(tri[1]);c=find(tri[2]);parent[b]=a;parent[c]=a
roots=np.array([find(i) for i in range(len(coord))]);rr=roots[inv[f[:,0]]]
report=[]
for root,count in sorted(zip(*np.unique(rr,return_counts=True)),key=lambda a:-a[1])[:25]:
 inds=np.flatnonzero(rr==root);pts=v[np.unique(f[inds])]
 report.append(dict(triangles=int(count),bounds=[pts.min(0).tolist(),pts.max(0).tolist()]))
cent=v[f].mean(1)
sections=[]
for x in [-.73,-.69,-.66,-.60,-.53,-.41,-.28,-.17,-.07,.03,.13,.23,.35,.49,.58]:
 sel=cent[np.abs(cent[:,0]-x)<.004]
 sections.append(dict(x=x,yz_quantiles=np.quantile(sel[:,1:],[0,.1,.25,.5,.75,.9,1],axis=0).tolist() if len(sel) else []))
(R/'source_landmarks.json').write_text(json.dumps(dict(bounds=[v.min(0).tolist(),v.max(0).tolist()],components=report,sections=sections),indent=2))
print(json.dumps(dict(bounds=[v.min(0).tolist(),v.max(0).tolist()],components=report[:6],sections=sections)),flush=True)
