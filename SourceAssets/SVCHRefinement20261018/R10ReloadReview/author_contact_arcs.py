"""Small smooth whole-arm approach/release arcs around the unchanged magazine."""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.spatial import ConvexHull
O=Path(__file__).parent;R9=O.parent/'R9ReloadGrip'
env={'__file__':str(R9/'author_reload_grip.py')}
exec(compile((R9/'author_reload_grip.py').read_text().split("report={'method'")[0],str(R9/'author_reload_grip.py'),'exec'),env)
globals().update({k:v for k,v in env.items() if k not in ('O','__file__','__builtins__')})
profile=json.loads((O/'profile_native_registration.json').read_text());clip=motion['clips']['reload']
layer=next(c for c in profile['clips'] if c['base']==clip['path'])
planes=np.unique(np.round(ConvexHull(mag['svch'][0]).equations,8),axis=0);report={'arcs':[]}
for label,window in [('approach',(12,20,43,49)),('release',(258,270,280,295))]:
 a,b,c,d=window;positions=[];weights=[]
 for f in range(a+1,d):
  base=np.asarray(clip['frames'][f]);world=comp(matrices(old_pose(base,layer,f/120)))
  p=points(np.linalg.inv(rigid(world[MAG])),skin(world,HANDIDS))
  # Far outside points cannot meet this shell within the 4 cm search window.
  distances=np.max(p@planes[:,:3].T+planes[:,3],axis=1)
  p=p[distances<4.5]
  positions.extend(p);weights.extend([float(ease(a,b,f)*(1-ease(c,d,f)))]*len(p))
 positions=np.asarray(positions);weights=np.asarray(weights)
 original=positions@planes[:,:3].T+planes[:,3]
 def constraint(v):return np.max(original+weights[:,None]*(planes[:,:3]@v)[None],axis=1)
 if constraint(np.zeros(3)).min()>=0:
  print('CONTACT_ARC_NOT_NEEDED',label,flush=True);continue
 best=None
 for start in [np.zeros(3)]+[np.eye(3)[i]*sign*3 for i in range(3) for sign in (1,-1)]:
  result=minimize(lambda v:float(v@v),start,method='SLSQP',bounds=[(-4,4)]*3,
   constraints=[{'type':'ineq','fun':constraint}],options={'maxiter':65,'ftol':.000001})
  print('ARC_CANDIDATE',label,result.success,result.x.tolist(),float(constraint(result.x).min()),flush=True)
  if result.success and (best is None or result.fun<best.fun):best=result
  if best is not None and np.linalg.norm(best.x)<2.5:break
 if best is None:raise RuntimeError('No bounded contact arc: '+label)
 entry={'name':label,'window_frames':window,'translation_magazine_cm':best.x.tolist(),
        'length_cm':float(np.linalg.norm(best.x)),'min_signed_mm':float(constraint(best.x).min()*10)}
 report['arcs'].append(entry);print('CONTACT_ARC',json.dumps(entry),flush=True)
(O/'contact_arcs.json').write_text(json.dumps(report,indent=2))
