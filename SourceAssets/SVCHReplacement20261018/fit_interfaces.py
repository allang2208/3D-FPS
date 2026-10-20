"""Author geometric registration against the accepted V9/R11 contact poses."""
import json,gzip,copy,sys
from pathlib import Path
import numpy as np,trimesh
from scipy.optimize import minimize
from scipy.spatial import ConvexHull
O=Path(__file__).parent;R11=O.parent/'SVCHRefinement20261018/R11ChargeHandoff';R9=R11.parent/'R9ReloadGrip'
env={'__file__':str(R9/'author_reload_grip.py')}
exec(compile((R9/'author_reload_grip.py').read_text().split("report={'method'")[0],str(R9/'author_reload_grip.py'),'exec'),env)
globals().update({k:v for k,v in env.items() if k not in ('O','__file__','__builtins__')})
motion=json.load(gzip.open(R11/'CurrentSource/motion.json.gz','rt'));profile=json.loads((R11/'profile_charge.json').read_text())
raw=json.load(gzip.open(O/'source_geometry.json.gz','rt'))
hold=json.loads((O.parent/'SVCHSketchfab20261017/Authoring/hold_frame.json').read_text());HR=np.array(hold['R']);HT=np.array(hold['t_cm'])
def native(v):
 g=(np.asarray(v)-HT)@HR;return np.column_stack((g[:,0]+18.7444,g[:,2],g[:,1]+1.5268))
def component(v):
 v=np.asarray(v);g=np.column_stack((v[:,0]-18.7444,v[:,2]-1.5268,v[:,1]));return g@HR.T+HT
def posed(role,frame):
 c=motion['clips'][role];e=next(c0 for c0 in profile['clips'] if c0['base']==c['path']);return comp(matrices(old_pose(np.array(c['frames'][frame]),e,c['times'][frame])))
def hand_in_bind(role,frame,side,anchor='WPN_root'):
 w=posed(role,frame);ids=np.flatnonzero(np.array([N[d].endswith('_'+side) and N[d].startswith(('hand_','thumb','index','middle','ring','pinky')) for d in DOM]))
 idx=NI[anchor];h=points(rest['svch'][idx]@np.linalg.inv(w[idx]),skin(w,ids));return native(h)
def mesh_part(key,group=None):
 a=raw[key];v=np.array(a['v']);t=np.array(a['t']);d=np.array(a['dom'])
 if group:t=t[(d[t]==group).all(1)]
 m=trimesh.Trimesh(v,t,process=True);m.remove_unreferenced_vertices();return m
grip=mesh_part('KVInhibitor.smd','tag_pistolgrip_attach');old=np.load(O/'old_grip.npz');oldgrip=trimesh.Trimesh(old['v'],old['t'],process=True)
hand=hand_in_bind('idle',0,'r');_,dist,_=trimesh.proximity.closest_point(oldgrip,hand);pad=np.argsort(dist)[:130]
# Retain the selected gun's entire shape: only a uniform unit conversion and
# rigid translation. Fit the fixed, approved hand, never finger or wrist poses.
def geom_at(x):return np.asarray(grip.vertices)*np.array([-x[0],-x[0],x[0]])+np.array([x[1],0,x[2]])
def loss(x):
 v=geom_at(x);m=trimesh.Trimesh(v,grip.faces,process=False);_,d,_=trimesh.proximity.closest_point(m,hand[pad])
 planes=ConvexHull(v).equations;signed=np.max(hand[::4]@planes[:,:3].T+planes[:,3],axis=1)
 pen=np.minimum(signed,0)
 return float(np.mean((d-dist[pad])**2)+10*np.mean(pen**2)+5*np.min(pen)**2+.05*(x[0]-8)**2)
fit=minimize(loss,[8.,18.,-12.],method='Powell',bounds=[(7.6,8.7),(15.,23.),(-15.,-10.)],options={'maxiter':16,'maxfev':650,'ftol':.0002})
S,TX,TZ=fit.x
source_to_native=np.diag([-S,-S,S,1.]);source_to_native[:3,3]=[TX,0,TZ]
receipt={'source_to_previous_native':source_to_native.tolist(),'uniform_cm_per_source_unit':S,'fit_loss':float(fit.fun),'right_grip_hand_and_wrist_unchanged':True,'source_geometry_reshaped':False,'source_animations_modified':False}
(O/'registration.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt),flush=True)
