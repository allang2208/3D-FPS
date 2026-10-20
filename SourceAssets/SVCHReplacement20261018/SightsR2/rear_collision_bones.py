"""Find rail positions clear of the preserved arm poses during bolt contact."""
import gzip,json
from pathlib import Path
import numpy as np,trimesh
from scipy.spatial import cKDTree
O=Path(__file__).parent;P=O.parents[2]
env={'__file__':str(O/'author_bolt_fit.py')}
exec(compile((O/'author_bolt_fit.py').read_text().split("c=motion['clips']['reload_empty']")[0],'contact_inputs','exec'),env)
motion,rest,ids,parents,matrices,old_pose=[env[k] for k in ('motion','rest','ids','parents','matrices','old_pose')]
with gzip.open(P/'SourceAssets/SVCHRefinement20261018/R9ReloadGrip/Inputs/arms.json.gz','rt') as f:a=json.load(f)
v=np.asarray(a['positions']);tri=np.asarray(a['triangles']);inv=np.linalg.inv(matrices(np.asarray(a['reference'])));weights=np.zeros((len(v),len(ids)))
for i,row in enumerate(a['weights']):
 for b,w in row:weights[i,ids[a['weight_bones'][b]]]=w
rear=np.asarray(json.loads((O/'sight_geometry.json').read_text())['SVCH_Detailed_rear']['v'])*[100,-100,100]
samples=rear[::50];offsets=np.array([0.]);profile=json.loads((O/'profile_bolt_fit.json').read_text());c=motion['clips']['reload_empty'];clip=next(x for x in profile['clips'] if x['base']==c['path'])
result={float(d):{'inside_samples':0,'min_clearance_cm':1e9} for d in offsets}
for frame in [285,315,345]:
 index=int(np.argmin(abs(np.asarray(c['times'])*120-frame)));t=c['times'][index];world=matrices(old_pose(np.asarray(c['frames'][index]),clip,t))
 for i,p in enumerate(parents):
  if p>=0:world[i]=world[p]@world[i]
 skin=np.zeros_like(v)
 for b in np.flatnonzero(weights.max(0)>0):
  m=world[b]@inv[b];skin+=(v@m[:3,:3].T+m[:3,3])*weights[:,b,None]
 m=rest[ids['WPN_root']]@np.linalg.inv(world[ids['WPN_root']]);skin=skin@m[:3,:3].T+m[:3,3]
 mesh=trimesh.Trimesh(skin,tri,process=True)
 query=np.concatenate([samples+[0,-float(d),0] for d in offsets]);dist=np.concatenate([trimesh.proximity.signed_distance(mesh,query[i:i+64]) for i in range(0,len(query),64)]).reshape(len(offsets),len(samples))
 for d,row in zip(offsets,dist):
  inside=query[row>.01];near=cKDTree(skin).query(inside)[1];from collections import Counter;print('COLLISION_BONES',frame,Counter(motion['names'][b] for b in weights[near].argmax(1)),flush=True);r=result[float(d)];r['inside_samples']+=int((row>.01).sum());r['min_clearance_cm']=min(r['min_clearance_cm'],float(abs(row).min()))
 print('REAR_CLEARANCE_FRAME',frame,flush=True)
(O/'rear_collision_bones.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
