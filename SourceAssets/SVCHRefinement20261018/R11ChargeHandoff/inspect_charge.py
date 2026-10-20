"""Read the current charging-hand pose and actual SVCH/SVD handle geometry."""
import gzip,json
from pathlib import Path
import numpy as np
import trimesh
O=Path(__file__).parent;R9=O.parent/'R9ReloadGrip';R10=O.parent/'R10ReloadReview'
env={'__file__':str(R9/'author_reload_grip.py')}
exec(compile((R9/'author_reload_grip.py').read_text().split("report={'method'")[0],str(R9/'author_reload_grip.py'),'exec'),env)
globals().update({k:v for k,v in env.items() if k not in ('O','__file__','__builtins__')})
motion=json.load(gzip.open(O/'CurrentSource/motion.json.gz','rt'))
profile=json.loads((R10/'profile_native_registration.json').read_text())
rightids=np.flatnonzero(np.array([N[b].endswith('_r') and N[b].startswith(('hand_','thumb','index','middle','ring','pinky')) for b in DOM]))
meshes={};report={'parts':{},'samples':[]}
for key in ('svch','svd'):
 v,t=geom(key,lambda n:('BoltCarrier' in n or 'ChargingHandle' in n));mesh=trimesh.Trimesh(vertices=v,faces=t,process=True)
 meshes[key]=mesh
 report['parts'][key]=[{'bounds':m.bounds.tolist(),'faces':len(m.faces),'center':m.centroid.tolist()} for m in mesh.split(only_watertight=False) if len(m.faces)>5]
clip=motion['clips']['reload_empty'];layer=next(c for c in profile['clips'] if c['base']==clip['path'])
for f in (268,280,290,300,310,320,340,350,360,380,400,515):
 src=comp(matrices(clip['frames'][f]));current=comp(matrices(old_pose(np.asarray(clip['frames'][f]),layer,f/120)))
 row={'frame':f,'hand_r':current[NI['hand_r'],:3,3].tolist(),'source_hand_r':src[NI['hand_r'],:3,3].tolist()}
 for key in ('svch','svd'):
  b=NI['WPN_bolt'];points_world=points(src[b]@np.linalg.inv(rest[key][b]),meshes[key].vertices)
  m=trimesh.Trimesh(vertices=points_world,faces=meshes[key].faces,process=False)
  skin_points=skin(current if key=='svch' else src,rightids)
  q,d,faces=trimesh.proximity.closest_point(m,skin_points)
  row[key]={'hand_surface_min_mm':float(d.min()*10),'hand_surface_p10_mm':float(np.percentile(d,10)*10),
            'bolt_position':src[b,:3,3].tolist()}
 report['samples'].append(row)
(O/'charge_geometry.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
