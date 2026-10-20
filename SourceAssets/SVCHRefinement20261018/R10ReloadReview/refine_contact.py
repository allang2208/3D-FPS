"""Bounded whole-hand clearance refinement; native finger/wrist locals stay frozen."""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
O=Path(__file__).parent;R9=O.parent/'R9ReloadGrip'
env={'__file__':str(R9/'author_reload_grip.py')}
exec(compile((R9/'author_reload_grip.py').read_text().split("report={'method'")[0],str(R9/'author_reload_grip.py'),'exec'),env)
globals().update({k:v for k,v in env.items() if k not in ('O','__file__','__builtins__')})
old=json.loads((R9/'profile_reload_grip.json').read_text());base=np.asarray(motion['clips']['reload']['frames'][220])
layer=next(c for c in old['clips'] if c['base']==motion['clips']['reload']['path']);pose=comp(matrices(old_pose(base,layer,220/120)))
inverse=np.linalg.inv(rigid(pose[MAG]));ids=HANDIDS[::3]
if (O/'contact_winding.json').exists():
 active=[v['vertex'] for v in json.loads((O/'contact_winding.json').read_text())['worst']]
 triangles=np.asarray(arms['triangles'])
 neighbors=np.unique(triangles[np.isin(triangles,active).any(axis=1)])
 ids=np.union1d(ids,neighbors)
hand=points(inverse,skin(pose,ids))
groups={d:np.array([j for j,v in enumerate(ids) if N[DOM[v]].startswith(d)]) for d in ('thumb','index','middle','ring','pinky')}
center=hand.mean(0)
_,_,distance=surfaces['svch'].nearest(hand)
goals={d:float(np.percentile(distance[ix],15)) for d,ix in groups.items()}
goals['thumb']=.2
body_v,body_t=geom('svch',lambda n:n in ('SVCH_Body','SVCH_Polymer','SVCH_Rubber','SVCH_BarrelSteel'))
bodies=[]
for kind in ('reload','reload_empty'):
 for f in (49,200,220,240,244):
  bp=comp(matrices(motion['clips'][kind]['frames'][f]));m=np.linalg.inv(rigid(bp[MAG]))@bp[ROOT]@np.linalg.inv(rest['svch'][ROOT])
  bodies.append(surface(points(m,body_v),body_t))
def transform(x):
 m=np.eye(4);m[:3,:3]=R.from_rotvec(x[3:]).as_matrix();m[:3,3]=center+x[:3]-m[:3,:3]@center;return m
def objective(x):
 moved=points(transform(x),hand);q,n,d=surfaces['svch'].nearest(moved);signed=np.einsum('ij,ij->i',moved-q,n)
 penetration=np.where(d<2.5,np.minimum(signed+.08,0),0)
 loss=30*np.mean(penetration**2)+8*np.min(penetration)**2
 for digit,ix in groups.items():
  loss+=(np.percentile(d[ix],15)-goals[digit])**2*(.4 if digit=='thumb' else 2.)
 for body in bodies:
  q,n,d=body.nearest(moved[::4]);s=np.einsum('ij,ij->i',moved[::4]-q,n)
  pen=np.where(d<2.5,np.minimum(s+.06,0),0)
  loss+=2*np.mean(pen**2)+.3*np.min(pen)**2
 loss+=.05*np.sum(x[:3]**2)+.8*np.sum(x[3:]**2)
 return float(loss)
initial=np.zeros(6)
if (O/'contact_refinement.json').exists():
 previous=json.loads((O/'contact_refinement.json').read_text())
 initial=np.r_[previous['translation_cm'],np.deg2rad(previous['rotation_deg'])]
result=minimize(objective,initial,method='Powell',bounds=[(-1.5,1.5)]*3+[(-np.deg2rad(12),np.deg2rad(12))]*3,
                options={'maxiter':22,'maxfev':1400,'xtol':.0003,'ftol':.00002})
delta=transform(result.x)
report={'delta_magazine_local':delta.tolist(),'translation_cm':result.x[:3].tolist(),
        'rotation_deg':np.rad2deg(result.x[3:]).tolist(),'before_objective':objective(np.zeros(6)),
        'after_objective':objective(result.x),'evaluations':result.nfev,'converged':bool(result.success)}
(O/'contact_refinement.json').write_text(json.dumps(report,indent=2));print('CONTACT_REFINED',json.dumps(report),flush=True)
