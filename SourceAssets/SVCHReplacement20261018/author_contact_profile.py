"""New contact registration only: immutable R11 local wrists/fingers and clocks."""
import json,gzip,copy,sys
from pathlib import Path
import numpy as np,trimesh
from scipy.optimize import minimize
from scipy.spatial import ConvexHull
O=Path(__file__).parent;R11=O.parent/'SVCHRefinement20261018/R11ChargeHandoff';R9=R11.parent/'R9ReloadGrip'
sys.path.insert(0,str(O));from contact_geometry import fit_surface
env={'__file__':str(R9/'author_reload_grip.py')}
exec(compile((R9/'author_reload_grip.py').read_text().split("report={'method'")[0],str(R9/'author_reload_grip.py'),'exec'),env)
globals().update({k:v for k,v in env.items() if k not in ('O','__file__','__builtins__')})
motion=json.load(gzip.open(R11/'CurrentSource/motion.json.gz','rt'));profile=json.loads((R11/'profile_charge.json').read_text());out=copy.deepcopy(profile)
raw=json.load(gzip.open(O/'source_geometry.json.gz','rt'));new=json.load(gzip.open(O/'new_geometry.json.gz','rt'));old=json.load(gzip.open(O/'previous_geometry.json.gz','rt'))
hold=json.loads((O.parent/'SVCHSketchfab20261017/Authoring/hold_frame.json').read_text());HR=np.array(hold['R']);HT=np.array(hold['t_cm']);SN=np.array(json.loads((O/'registration.json').read_text())['source_to_previous_native'])
def component(n):
 n=np.asarray(n);return np.column_stack((n[:,0]-18.7444,n[:,2]-1.5268,n[:,1]))@HR.T+HT
def src_component(v):return component(np.asarray(v)@SN[:3,:3].T+SN[:3,3])
def native(v):
 g=(np.asarray(v)-HT)@HR;return np.column_stack((g[:,0]+18.7444,g[:,2],g[:,1]+1.5268))
def mesh(v,t):
 m=trimesh.Trimesh(v,t,process=True);m.remove_unreferenced_vertices();return m
def source_part(key,group,knob=False):
 a=raw[key];v=fit_surface(np.array(a['v']),a['dom'],key);t=np.array(a['t']);d=np.array(a['dom']);valid=(d==group) if group else np.ones(len(v),bool)
 if knob:valid&=v[:,1]<-.28
 t=t[valid[t].all(1)];return mesh(src_component(v),t)
def oldpart(key):a=old[key];return mesh(a['v'],a['t'])
def newpart(key):a=new[key];return mesh(a['v'],a['t'])
def posed(role,i):
 c=motion['clips'][role];layer=next(e for e in profile['clips'] if e['base']==c['path']);return comp(matrices(old_pose(np.asarray(c['frames'][i]),layer,c['times'][i])))
def hand(role,i,side,anchor):
 w=posed(role,i);ids=np.flatnonzero(np.array([N[d].endswith('_'+side) and N[d].startswith(('hand_','thumb','index','middle','ring','pinky')) for d in DOM]));b=NI[anchor]
 return points(rest['svch'][b]@np.linalg.inv(w[b]),skin(w,ids))
gr=np.load(O/'old_grip.npz');og=mesh(component(gr['v']),gr['t']);ng=source_part('KVInhibitor.smd','tag_pistolgrip_attach')
ob=oldpart('SM_SVCH_BoltCarrier');ob=max((m for m in ob.split(only_watertight=False) if len(m.faces)>50),key=lambda m:m.centroid[0]);nb=source_part('KVInhibitor.smd','j_charging_handle',True)
om=oldpart('SM_SVCH_Magazine');nm=newpart('SVCH_New_mag')
body=oldpart('SM_SVCH_Body');nv=native(body.vertices);sel=(nv[:,0]>24)&(nv[:,0]<45)&(nv[:,2]<8.3);body=mesh(body.vertices,body.faces[sel[body.faces].all(1)])
barrel=newpart('SVCH_New_barrel');nv=native(barrel.vertices);sel=(nv[:,0]>24)&(nv[:,0]<45)&(nv[:,2]<6.5);barrel=mesh(barrel.vertices,barrel.faces[sel[barrel.faces].all(1)])
report={'source_profile':'R11ChargeHandoff/profile_charge.json','source_animations_modified':False,'native_V9_modified':False,'only_changed_bones':['clavicle_l','clavicle_r'],'fits':{},'runtime_tested':False}
maps={}
for name,oldmesh,newmesh,role,frame,side,anchor in [('grip',og,ng,'idle',0,'r','WPN_root'),('support',body,barrel,'idle',0,'l','WPN_root'),('magazine',om,nm,'reload',220,'l','WPN_SOCKET_Magazine'),('bolt',ob,nb,'reload_empty',320,'r','WPN_bolt')]:
 h=hand(role,frame,side,anchor);_,dist,_=trimesh.proximity.closest_point(oldmesh,h);pads=np.argsort(dist)[:100]
 oldcenter=oldmesh.bounds.mean(0);newcenter=newmesh.bounds.mean(0)
 planes=np.unique(np.round(ConvexHull(newmesh.vertices).equations,7),axis=0)
 oldplanes=np.unique(np.round(ConvexHull(oldmesh.vertices).equations,7),axis=0)
 # A convex envelope spans the grip's concave finger recesses. Preserve the
 # source envelope allowance per vertex instead of treating those voids as skin.
 baseline=np.minimum(np.max(h[::3]@oldplanes[:,:3].T+oldplanes[:,3],axis=1),0.)
 def mapping(x):
  m=np.eye(4);m[:3,:3]=R.from_rotvec(x[3:]).as_matrix();m[:3,3]=newcenter+x[:3]-m[:3,:3]@oldcenter;return m
 def clearance(x):return np.max(points(mapping(x),h[::3])@planes[:,:3].T+planes[:,3],axis=1)-baseline-.01
 def loss(x):
  m=mapping(x);_,d,_=trimesh.proximity.closest_point(newmesh,points(m,h[pads]));pen=np.minimum(clearance(x),0)
  return float(np.mean((d-dist[pads])**2)+25*np.mean(pen**2)+10*np.min(pen)**2+.05*np.sum(x[:3]**2)+1.*np.sum(x[3:]**2))
 bounds=[(-3.,3.)]*3+[(-.35,.35)]*3
 fit=minimize(loss,np.zeros(6),method='Powell',bounds=bounds,options={'maxiter':15,'maxfev':850,'ftol':.0003})
 # Constrain the closed hand against the convex grasp envelope. This is part
 # of authoring the rigid fit, not a change to source wrist/finger animation.
 constrained=minimize(loss,fit.x,method='SLSQP',bounds=bounds,constraints=[{'type':'ineq','fun':clearance}],options={'maxiter':100,'ftol':1e-6})
 chosen=constrained if constrained.success else fit
 m=mapping(chosen.x);maps[name]=(anchor,m)
 report['fits'][name]={'bind_component_mapping':m.tolist(),'loss':float(chosen.fun),'clearance_constrained':bool(constrained.success),'min_envelope_clearance_cm':float(clearance(chosen.x).min()),'offset_cm':chosen.x[:3].tolist(),'rotation_deg':np.rad2deg(chosen.x[3:]).tolist()}
 print('AUTHORED_RIGID_CONTACT',name,json.dumps(report['fits'][name]),flush=True)
def world_map(name,w):
 anchor,m=maps[name];b=NI[anchor];a=w[b]@np.linalg.inv(rest['svch'][b]);return a@m@np.linalg.inv(a)
for role,c in motion['clips'].items():
 before=next(x for x in profile['clips'] if x['base']==c['path']);dst=next(x for x in out['clips'] if x['base']==c['path']);vals={'l':[],'r':[]}
 for i,t in enumerate(c['times']):
  base=np.asarray(c['frames'][i]);local=old_pose(base,before,t);w=comp(matrices(local));frame=t*120
  magweight=float(ease(0,20,frame)*(1-ease(280,302,frame))) if role in ('reload','reload_empty') else 0.
  chargeweight=float(ease(260,286,frame)*(1-ease(350,400,frame))) if role=='reload_empty' else 0.
  for side,first,second,weight in [('l','support','magazine',magweight),('r','grip','bolt',chargeweight)]:
   ci=NI['clavicle_'+side];target=mix(world_map(first,w)@w[ci],world_map(second,w)@w[ci],weight)
   loc=np.linalg.solve(w[PI[ci]],target);rot=R.from_matrix(rigid(loc)[:3,:3])*R.from_quat(base[ci,3:7]).inv()
   v=[*(loc[:3,3]-base[ci,:3]),*rot.as_quat(),*(local[ci,7:]-base[ci,7:])]
   if vals[side] and np.dot(vals[side][-1][3:7],v[3:7])<0:v[3:7]=[-x for x in v[3:7]]
   vals[side].append(v)
 dst['tracks']=[x for x in dst['tracks'] if x['bone'] not in ('clavicle_l','clavicle_r')]+[{'bone':'clavicle_'+s,'times':c['times'],'values':np.round(vals[s],10).ravel().tolist()} for s in ('l','r')]
(O/'profile_replacement.json').write_text(json.dumps(out,separators=(',',':')))
(O/'contact_authoring_receipt.json').write_text(json.dumps(report,indent=2));print('SVCH_CONTACT_PROFILE_AUTHORED',flush=True)
