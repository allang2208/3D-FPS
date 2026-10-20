"""Register the existing right-hand charge gesture to the SVCH handle as a rigid arm."""
import copy,gzip,json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.spatial import ConvexHull
import trimesh
O=Path(__file__).parent;R9=O.parent/'R9ReloadGrip';R10=O.parent/'R10ReloadReview'
env={'__file__':str(R9/'author_reload_grip.py')}
exec(compile((R9/'author_reload_grip.py').read_text().split("report={'method'")[0],str(R9/'author_reload_grip.py'),'exec'),env)
globals().update({k:v for k,v in env.items() if k not in ('O','__file__','__builtins__')})
motion=json.load(gzip.open(O/'CurrentSource/motion.json.gz','rt'))
profile=json.loads((R10/'profile_native_registration.json').read_text());output=copy.deepcopy(profile)
clip=motion['clips']['reload_empty'];old=next(c for c in profile['clips'] if c['base']==clip['path'])
dst=next(c for c in output['clips'] if c['base']==clip['path'])
bolt=NI['WPN_bolt'];hand=NI['hand_r'];clav=NI['clavicle_r']
rightids=np.flatnonzero(np.array([N[b].endswith('_r') and N[b].startswith(('hand_','thumb','index','middle','ring','pinky')) for b in DOM]))
source_v,source_t=geom('svd',lambda n:'ChargingHandle' in n)
target_v,target_t=geom('svch',lambda n:'BoltCarrier' in n)
parts=trimesh.Trimesh(vertices=target_v,faces=target_t,process=True).split(only_watertight=False)
knob=max((m for m in parts if len(m.faces)>50),key=lambda m:m.centroid[0])
source_v=points(np.linalg.inv(rigid(rest['svd'][bolt])),source_v)
target_v=points(np.linalg.inv(rigid(rest['svch'][bolt])),knob.vertices)
source_mesh=trimesh.Trimesh(vertices=source_v,faces=source_t,process=True)
target_mesh=trimesh.Trimesh(vertices=target_v,faces=knob.faces,process=True)
source_center=(source_v.min(0)+source_v.max(0))*.5;target_center=(target_v.min(0)+target_v.max(0))*.5
shift=target_center-source_center
native=comp(matrices(clip['frames'][320]));current=comp(matrices(old_pose(np.asarray(clip['frames'][320]),old,320/120)))
skin_points=points(np.linalg.inv(rigid(current[bolt])),skin(current,rightids))
q,d,ids=trimesh.proximity.closest_point(source_mesh,skin_points)
pads=np.argsort(d)[:120];selected=skin_points[pads];desired=d[pads]
planes=np.unique(np.round(ConvexHull(target_v).equations,8),axis=0)
def transform(x):
 m=np.eye(4);m[:3,:3]=R.from_rotvec(x[3:]).as_matrix();m[:3,3]=target_center+x[:3]-m[:3,:3]@source_center;return m
def objective(x):
 moved=points(transform(x),selected);q,dist,ids=trimesh.proximity.closest_point(target_mesh,moved)
 whole=points(transform(x),skin_points[::3]);signed=np.max(whole@planes[:,:3].T+planes[:,3],axis=1)
 pen=np.minimum(signed-.02,0)
 return float(np.mean((dist-desired)**2)+10*np.mean(pen**2)+4*np.min(pen)**2+.04*np.sum(x[:3]**2)+.8*np.sum(x[3:]**2))
fit=minimize(objective,np.zeros(6),method='Powell',bounds=[(-.8,.8)]*3+[(-np.deg2rad(8),np.deg2rad(8))]*3,
 options={'maxiter':18,'maxfev':700,'ftol':.0001})
def outside_handle(x):
 moved=points(transform(x),skin_points)
 return np.max(moved@planes[:,:3].T+planes[:,3],axis=1)-.015
best=None
for offset in (np.zeros(3),np.array([-1.,0.,0.]),np.array([0.,0.,1.]),np.array([0.,1.,0.])):
 start=fit.x.copy();start[:3]=np.clip(start[:3]+offset,-2.,2.)
 clearance=minimize(objective,start,method='SLSQP',bounds=[(-2.,2.)]*3+[(-np.deg2rad(15),np.deg2rad(15))]*3,
  constraints=[{'type':'ineq','fun':outside_handle}],options={'maxiter':100,'ftol':.00001})
 if clearance.success and (best is None or clearance.fun<best.fun):best=clearance
 if best is not None:break
if best is None:raise RuntimeError('No handle-clear rigid fit: '+clearance.message)
fit=best
mapping=transform(fit.x);values=[];stats=[]
for i,t in enumerate(clip['times']):
 base=np.asarray(clip['frames'][i]);local=old_pose(base,old,t);world=comp(matrices(local));anchor=rigid(world[bolt])
 weight=float(ease(260,286,t*120)*(1-ease(350,400,t*120)))
 desired=anchor@mapping@np.linalg.inv(anchor)@world[hand]
 target=mix(world[hand],desired,weight);registration=target@np.linalg.inv(world[hand]);new_clav=registration@world[clav]
 loc=np.linalg.solve(world[PI[clav]],new_clav)
 rotation=R.from_matrix(rigid(loc)[:3,:3])*R.from_quat(base[clav,3:7]).inv()
 if weight<1e-9:
  rotation=R.from_quat(local[clav,3:7])*R.from_quat(base[clav,3:7]).inv()
  loc[:3,3]=local[clav,:3]
 v=[*(loc[:3,3]-base[clav,:3]),*rotation.as_quat(),*(local[clav,7:]-base[clav,7:])]
 if values and np.dot(values[-1][3:7],v[3:7])<0:v[3:7]=[-x for x in v[3:7]]
 values.append(v)
 if 286<=i<=350 and i%4==0:
  moved=points(mapping,points(np.linalg.inv(anchor),skin(world,rightids)))
  q,d,ids=trimesh.proximity.closest_point(target_mesh,moved)
  before=points(np.linalg.inv(anchor),skin(world,rightids));_,bd,_=trimesh.proximity.closest_point(target_mesh,before)
  stats.append({'frame':i,'before_min_mm':float(bd.min()*10),'after_min_mm':float(d.min()*10),
                'after_pad_median_mm':float(np.median(d[pads])*10)})
dst['tracks']=[tr for tr in dst['tracks'] if tr['bone']!='clavicle_r']+[{'bone':'clavicle_r','times':clip['times'],'values':np.round(values,10).ravel().tolist()}]
report={'changed_action':'reload_empty','changed_tracks':['clavicle_r'],
 'native_hand_fingers_arm_joints_preserved':True,'window_frames':[260,286,350,400],
 'source_handle_center_cm':source_center.tolist(),'target_handle_center_cm':target_center.tolist(),
 'mapping_bolt_local':mapping.tolist(),'nominal_translation_cm':shift.tolist(),
 'fit_translation_cm':fit.x[:3].tolist(),'fit_rotation_deg':np.rad2deg(fit.x[3:]).tolist(),'samples':stats}
(O/'profile_charge.json').write_text(json.dumps(output,separators=(',',':')))
(O/'charge_receipt.json').write_text(json.dumps(report,indent=2))
print('SVCH_CHARGE_AUTHORED',json.dumps(report),flush=True)
