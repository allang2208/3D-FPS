import gzip,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
O=Path(__file__).parent;P=O.parents[2]
def load(p):
 with gzip.open(p,'rt',encoding='utf-8') as f:return json.load(f)
motion=load(P/'SourceAssets/SVCHRefinement20261018/R11ChargeHandoff/CurrentSource/motion.json.gz')
ref=load(P/'SourceAssets/SVCHRefinement20261018/R9ReloadGrip/Inputs/svch.json.gz')
profile=json.loads((O.parent/'profile_replacement.json').read_text())
geom=load(O.parent/'new_geometry.json.gz')
names=motion['names'];ids={n:i for i,n in enumerate(names)};parents=[ids.get(p,-1) for p in motion['parents']]
def matrices(rows):
 out=np.tile(np.eye(4),(len(rows),1,1));out[:,:3,3]=rows[:,:3];out[:,:3,:3]=R.from_quat(rows[:,3:7]).as_matrix()*rows[:,None,7:10];return out
rest=matrices(np.asarray(ref['reference']))
report={}
for role in ('idle','aim'):
 c=motion['clips'][role];rows=np.asarray(c['frames'][0]).copy();layer=next(x for x in profile['clips'] if x['base']==c['path'])
 for track in layer['tracks']:
  i=ids[track['bone']];v=np.asarray(track['values']).reshape(-1,10)[0];rows[i,:3]+=v[:3];rows[i,3:7]=(R.from_quat(v[3:7])*R.from_quat(rows[i,3:7])).as_quat();rows[i,7:]+=v[7:]
 world=matrices(rows)
 for i,p in enumerate(parents):
  if p>=0:world[i]=world[p]@world[i]
 out={}
 for ob,d in geom.items():
  for bone in sorted(set(d['dom'])):
   if bone=='WPN_root':continue
   v=np.asarray(d['v'])[np.asarray(d['dom'])==bone];i=ids[bone];r=ids['WPN_root'];x=rest[r]@np.linalg.inv(world[r])@world[i]@np.linalg.inv(rest[i]);posed=v@x[:3,:3].T+x[:3,3]
   out[ob+'/'+bone]={'max_delta_cm':float(np.linalg.norm(posed-v,axis=1).max()),'rest_bounds':[v.min(0).tolist(),v.max(0).tolist()],'posed_bounds':[posed.min(0).tolist(),posed.max(0).tolist()]}
 report[role]=out
(O/'offline_mechanics.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
