"""Small whole-arm release clearance; keep native wrist/fingers and bolt timing."""
import gzip,json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.spatial import ConvexHull
import trimesh
O=Path(__file__).parent;R9=O.parent/'R9ReloadGrip'
env={'__file__':str(R9/'author_reload_grip.py')}
exec(compile((R9/'author_reload_grip.py').read_text().split("report={'method'")[0],str(R9/'author_reload_grip.py'),'exec'),env)
globals().update({k:v for k,v in env.items() if k not in ('O','__file__','__builtins__')})
motion=json.load(gzip.open(O/'CurrentSource/motion.json.gz','rt'));clip=motion['clips']['reload_empty']
profile=json.loads((O/'profile_charge.json').read_text());layer=next(c for c in profile['clips'] if c['base']==clip['path'])
receipt=json.loads((O/'charge_receipt.json').read_text());assert not receipt.get('release_clearance'),'Run author_charge first to start from rigid registration'
clav=NI['clavicle_r'];bolt=NI['WPN_bolt'];track=next(t for t in layer['tracks'] if t['bone']=='clavicle_r');values=np.asarray(track['values']).reshape((-1,10))
v,t=geom('svch',lambda n:'BoltCarrier' in n);parts=trimesh.Trimesh(vertices=v,faces=t,process=True).split(only_watertight=False)
knob=max((m for m in parts if len(m.faces)>50),key=lambda m:m.centroid[0]);kv=points(np.linalg.inv(rigid(rest['svch'][bolt])),knob.vertices)
planes=np.unique(np.round(ConvexHull(kv).equations,8),axis=0)
ids=np.flatnonzero(np.array([N[d].endswith('_r') and N[d].startswith(('hand_','thumb','index','middle','ring','pinky')) for d in DOM]))
def bump(i,start,peak,end):return float(ease(start,peak,i)*(1-ease(peak,end,i)))
arcs=[]
for start,peak,end in [(303,307,310),(344,346,356)]:
 poses={};clouds=[];weights=[]
 for i in range(start+1,end):
  local=old_pose(np.asarray(clip['frames'][i]),layer,clip['times'][i]);world=comp(matrices(local));poses[i]=world
  clouds.append(points(np.linalg.inv(rigid(world[bolt])),skin(world,ids)));weights.append(bump(i,start,peak,end))
 clouds=np.asarray(clouds);weights=np.asarray(weights)
 def clearance(x):
  moved=clouds+weights[:,None,None]*x[None,None,:]
  return np.max(moved@planes[:,:3].T+planes[:,3],axis=-1).ravel()-.005
 best=None
 for axis in ([0,0,0],[1,0,0],[-1,0,0],[0,1,0],[0,-1,0],[0,0,1],[0,0,-1]):
  fit=minimize(lambda x:float(x@x),np.array(axis,dtype=float),method='SLSQP',bounds=[(-2.5,2.5)]*3,
   constraints=[{'type':'ineq','fun':clearance}],options={'maxiter':80,'ftol':1e-8})
  if fit.success and (best is None or fit.fun<best.fun):best=fit
 if best is None:raise RuntimeError('No native release clearance')
 for i,world in poses.items():
  shift=rigid(world[bolt])[:3,:3]@best.x*bump(i,start,peak,end)
  parent=world[PI[clav]];values[i,:3]+=np.linalg.solve(parent[:3,:3],shift)
 arcs.append({'frames':[start,peak,end],'peak_translation_bolt_cm':best.x.tolist(),'peak_distance_mm':float(np.linalg.norm(best.x)*10),
  'min_envelope_clearance_mm':float(clearance(best.x).min()*10+.05)})
track['values']=np.round(values,10).ravel().tolist()
(O/'profile_charge.json').write_text(json.dumps(profile,separators=(',',':')))
receipt['release_clearance']=arcs;(O/'charge_receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(arcs),flush=True)
