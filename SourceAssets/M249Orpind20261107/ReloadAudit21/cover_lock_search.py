from pathlib import Path
import json,numpy as np
from mathutils import Quaternion
from mathutils.bvhtree import BVHTree
r=Path(__file__).resolve().parent;folder=r/'cover_before/box_empty_base_right';meta=json.loads((folder/'geometry.json').read_text());j=json.loads((folder/'review.json').read_text());ns=meta['bones'];dom=np.fromfile(folder/'dominant.bin',np.uint32);pa=np.fromfile(folder/'poses.f32',np.float32).reshape(-1,4+len(ns)*7)
def rot(q):return np.array(Quaternion((q[3],q[0],q[1],q[2])).to_matrix())
def get(row):
 stem=folder/Path(row['file']).stem;v=np.fromfile(stem.with_suffix('.vertices'),np.float32).reshape(-1,3);f=np.fromfile(stem.with_suffix('.indices'),np.uint32).reshape(-1,3);m=np.fromfile(stem.with_suffix('.materials'),np.uint32);p=pa[np.argmin(abs(pa[:,1]-row['source'])),4:].reshape(-1,7);return v,f,m,p
ref=min(j['frames'],key=lambda x:abs(x['source']-4.5));v,f,m,p=get(ref);cover=ns.index('PKM_Cover');hand=ns.index('hand_r');hf=f[np.array([n.endswith('_r') and n.startswith(('hand','thumb','index','middle','ring','pinky')) for n in ns])[dom[f]].all(1)];local=(v-p[cover,:3])@rot(p[cover,3:]);trees=[BVHTree.FromPolygons(v.tolist(),f[m==meta['slots'].index(slot)].tolist(),all_triangles=True) for slot in ['M249_Factory_Cover','M249_OpticalHousing']];found=[]
for direction in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]:
 for distance in np.arange(.25,5.01,.25):
  offset=np.array(direction)*distance;vv=v+rot(p[cover,3:])@offset;a=BVHTree.FromPolygons(vv.tolist(),hf.tolist(),all_triangles=True)
  if not any(a.overlap(t) for t in trees):found.append((float(distance),offset.tolist()));break
print('reference',ref['source'],'choices',found,flush=True)
for distance,offset in sorted(found):
 print('OFFSET',offset,flush=True)
 for row in j['frames']:
  if not 4.3<row['source']<4.86:continue
  v2,f2,m2,p2=get(row);vv=(local+np.array(offset))@rot(p2[cover,3:]).T+p2[cover,:3];a=BVHTree.FromPolygons(vv.tolist(),hf.tolist(),all_triangles=True);counts=[]
  for slot in ['M249_Factory_Cover','M249_OpticalHousing','M249_Factory_Receiver']:
   b=BVHTree.FromPolygons(v2.tolist(),f2[m2==meta['slots'].index(slot)].tolist(),all_triangles=True);counts.append(len(set(x for x,y in a.overlap(b))))
  print(round(row['source'],3),counts,flush=True)
