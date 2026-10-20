"""Fit the unchanged hand outside a conservative closed magazine envelope."""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.spatial import ConvexHull
O=Path(__file__).parent;R9=O.parent/'R9ReloadGrip'
env={'__file__':str(R9/'author_reload_grip.py')}
exec(compile((R9/'author_reload_grip.py').read_text().split("report={'method'")[0],str(R9/'author_reload_grip.py'),'exec'),env)
globals().update({k:v for k,v in env.items() if k not in ('O','__file__','__builtins__')})
old=json.loads((R9/'profile_reload_grip.json').read_text());clip=motion['clips']['reload'];base=np.asarray(clip['frames'][220])
layer=next(c for c in old['clips'] if c['base']==clip['path']);pose=comp(matrices(old_pose(base,layer,220/120)))
inverse=np.linalg.inv(rigid(pose[MAG]));hand=points(inverse,skin(pose,HANDIDS));center=hand.mean(0)
groups={d:np.array([j for j,v in enumerate(HANDIDS) if N[DOM[v]].startswith(d)]) for d in ('thumb','index','middle','ring','pinky')}
planes=np.unique(np.round(ConvexHull(mag['svch'][0]).equations,8),axis=0)
def transform(x):
 m=np.eye(4);m[:3,:3]=R.from_rotvec(x[3:]).as_matrix();m[:3,3]=center+x[:3]-m[:3,:3]@center;return m
def distances(x):return np.max(points(transform(x),hand)@planes[:,:3].T+planes[:,3],axis=1)
def objective(x):
 d=distances(x);pen=np.minimum(d-.04,0)
 loss=40*np.mean(pen**2)+30*np.min(pen)**2
 for digit,ix in groups.items():
  goal={'thumb':.2,'index':.15,'middle':.2,'ring':.25,'pinky':.4}[digit]
  loss+=(np.percentile(d[ix],10)-goal)**2*(.3 if digit=='thumb' else 1.)
 loss+=.025*np.sum(x[:3]**2)+.3*np.sum(x[3:]**2)
 return float(loss)
prior=json.loads((O/'contact_refinement.json').read_text());start=np.r_[prior['translation_cm'],np.deg2rad(prior['rotation_deg'])]
result=minimize(objective,start,method='Powell',bounds=[(-2.3,2.3)]*3+[(-np.deg2rad(28),np.deg2rad(28))]*3,
 options={'maxiter':30,'maxfev':2400,'xtol':.0001,'ftol':.000001})
constrained=minimize(objective,result.x,method='SLSQP',bounds=[(-2.3,2.3)]*3+[(-np.deg2rad(28),np.deg2rad(28))]*3,
 constraints=[{'type':'ineq','fun':lambda x:distances(x)-.02}],options={'maxiter':80,'ftol':.00001})
if constrained.success:result=constrained
d=distances(result.x)
report={'method':'Conservative closed convex magazine envelope; all native hand vertices',
 'delta_magazine_local':transform(result.x).tolist(),'translation_cm':result.x[:3].tolist(),'rotation_deg':np.rad2deg(result.x[3:]).tolist(),
 'before_objective':objective(np.zeros(6)),'after_objective':objective(result.x),'evaluations':result.nfev,'closed_envelope_constraint_satisfied':bool(constrained.success),
 'envelope_min_signed_mm':float(d.min()*10),'digit_p10_mm':{k:float(np.percentile(d[v],10)*10) for k,v in groups.items()}}
(O/'contact_refinement.json').write_text(json.dumps(report,indent=2));print('SOLID_CONTACT_REFINED',json.dumps(report),flush=True)
