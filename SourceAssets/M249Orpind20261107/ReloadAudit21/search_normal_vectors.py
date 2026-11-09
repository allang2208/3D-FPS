from pathlib import Path
import bpy,json,numpy as np
from mathutils.bvhtree import BVHTree
from mathutils import Quaternion
r=Path(__file__).resolve().parent;result={}
for folder in (r/'surface_final').iterdir():
 if folder.name!='box_normal_base_right':continue
 meta=json.loads((folder/'geometry.json').read_text());j=json.loads((folder/'review.json').read_text());ns=meta['bones'];dom=np.fromfile(folder/'dominant.bin',np.uint32);hand=np.array([n.endswith('_r') and n.startswith(('hand','thumb','index','middle','ring','pinky')) for n in ns])[dom];pa=np.fromfile(folder/'poses.f32',np.float32).reshape(-1,4+len(ns)*7);rr=[]
 for row in j['frames']:
  if not 5.26<row['source']<5.29:continue
  stem=folder/Path(row['file']).stem;v=np.fromfile(stem.with_suffix('.vertices'),np.float32).reshape(-1,3);f=np.fromfile(stem.with_suffix('.indices'),np.uint32).reshape(-1,3);m=np.fromfile(stem.with_suffix('.materials'),np.uint32);hf=f[hand[f].all(1)];p=pa[np.argmin(abs(pa[:,1]-row['source'])),4:].reshape(-1,7);q=p[ns.index('WPN_root'),3:];rot=np.array(Quaternion((q[3],q[0],q[1],q[2])).to_matrix());trees={name:BVHTree.FromPolygons(v.tolist(),f[m==meta['slots'].index(name)].tolist(),all_triangles=True) for name in ['M249_OpticalHousing','M249_Factory_Cover','M249_Factory_Receiver']};values=[]
  for offset in [(0,0,0),(0,0,1),(0,0,2),(0,0,4),(0,0,8),(0,0,-2),(0,2,0),(0,-2,0),(-2,0,0),(-4,0,0),(-8,0,0)]:
   arm=BVHTree.FromPolygons((v+rot@np.array(offset)).tolist(),hf.tolist(),all_triangles=True);values.append([len(set(x for x,y in arm.overlap(tree))) for tree in trees.values()])
  rr.append(dict(source=row['source'],offsets=values));print(folder.name,round(row['source'],3),values,flush=True)
 result[folder.name]=rr
(r/'clearance_normal_vectors.json').write_text(json.dumps(result,indent=2))
