import json,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;d=json.loads((O/'grip_input.json').read_text(encoding='utf-8'))
axes=[np.arange(-.065,.136,.002),np.arange(.005,.246,.002),np.arange(-.275,-.054,.002)]
arrays={}
for name in ('M870_body','M870_trigger'):
 g=d['geometry'][name];tree=BVHTree.FromPolygons(g['points'],g['faces']);values=np.empty(tuple(len(v) for v in axes),dtype=np.float32)
 for i,x in enumerate(axes[0]):
  for j,y in enumerate(axes[1]):
   for k,z in enumerate(axes[2]):
    p=Vector((x,y,z));q,n,fi,dist=tree.find_nearest(p);values[i,j,k]=dist if (p-q).dot(n)>=0 else -dist
 arrays[name]=values
 print('CONTACT_FIELD',name,values.shape,flush=True)
g=d['geometry']['M870_trigger'];v=[Vector(p) for p in g['points']];front=[]
forward=Vector((0,1,0))
for f in g['faces']:
 normal=(v[f[1]]-v[f[0]]).cross(v[f[2]]-v[f[0]]).normalized()
 if normal.dot(forward)>.5:front.append(f)
tree=BVHTree.FromPolygons(g['points'],front);samples=[]
for i in d['hand_ids']:
 if d['weights'][i].get('index_03_r',0)>.85:
  p=Vector(d['reference_points'][i]);q,n,fi,dist=tree.find_nearest(p);samples.append((dist,i,list(q),list(n)))
samples.sort();patch=samples[:8]
(O/'trigger_pad.json').write_text(json.dumps({'vertices':[s[1] for s in patch],'targets':[s[2] for s in patch],'normals':[s[3] for s in patch]},indent=2))
np.savez_compressed(O/'contact_fields.npz',x=axes[0],y=axes[1],z=axes[2],**arrays)
print('TRIGGER_PAD',patch[:2],flush=True)
