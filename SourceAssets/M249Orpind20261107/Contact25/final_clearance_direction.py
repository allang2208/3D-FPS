from pathlib import Path
import json,numpy as np
from mathutils import Vector,Quaternion
from mathutils.bvhtree import BVHTree
r=Path(__file__).resolve().parent;folder=r/'verified/45_empty_canted_left'
j=json.loads((folder/'review.json').read_text());meta=json.loads((folder/'geometry.json').read_text())
row=min(j['frames'],key=lambda f:abs(f['source']-2.985096));stem=folder/Path(row['file']).stem
v=np.fromfile(stem.with_suffix('.vertices'),np.float32).reshape(-1,3);dom=np.fromfile(folder/'dominant.bin',np.uint32)
arm=np.array([n.endswith('_l') and n.startswith(('hand','index','middle','ring','pinky','thumb')) for n in meta['bones']])[dom]
p=Path(str(stem)+'_SM_m249_side_mag_45.vertices');pv=np.fromfile(p,np.float32).reshape(-1,3);faces=np.fromfile(p.with_suffix('.indices'),np.uint32).reshape(-1,3);tree=BVHTree.FromPolygons(pv.tolist(),faces.tolist(),all_triangles=True)
src=(r/'depths.py').read_text();ns={'np':np};exec(src[src.index('def winding'):src.index('for folder in sorted')],ns)
ids=np.flatnonzero(arm&np.all(v>=pv.min(0),axis=1)&np.all(v<=pv.max(0),axis=1));hits=[tree.find_nearest(Vector(v[i])) for i in ids]
candidate=[k for k,h in enumerate(hits) if .15<h[3]<.3]
ids=ids[candidate];wn=ns['winding'](v[ids],pv[faces].astype(np.float64));chosen=[(i,hits[k]) for i,k,inside in zip(ids,candidate,wn>.65) if inside]
delta=np.array([np.array(hit[0])-v[i] for i,hit in chosen]);direction=delta.mean(0);direction/=np.linalg.norm(direction)
raw=np.fromfile(folder/'poses.f32',np.float32).reshape(-1,4+j['bone_count']*7);fr=raw[np.argmin(abs(raw[:,0]-row['runtime'])),4:].reshape(-1,7);q=fr[meta['bones'].index('WPN_root'),3:7];rotation=np.array(Quaternion((q[3],*q[:3])).to_matrix());local=rotation.T@direction
out=dict(source=row['source'],direction_gun_local=local.tolist(),vertices=len(chosen),offset_cm=.14)
(r/'final_clearance_direction.json').write_text(json.dumps(out,indent=2));print(out,flush=True)
