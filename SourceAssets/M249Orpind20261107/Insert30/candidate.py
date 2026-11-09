"""Keep palm contacts; move the bent elbow below the near-camera silhouette."""
from common import *
import json,pickle
from scipy.ndimage import gaussian_filter1d
from scipy.interpolate import PchipInterpolator
h=s['hinge'];output={};report={}
def smooth(x):
 x=np.clip(x,0,1);return x*x*x*(10+x*(-15+6*x))
def return_phase(times,empty):
 folder=r/'before'/('30_empty_base'if empty else '30_normal_base')
 j=json.loads((folder/'review.json').read_text());a=np.fromfile(folder/'poses.f32',np.float32).reshape(-1,4+j['bone_count']*7)
 source,ids=np.unique(a[:,1],return_index=True);runtime=a[ids,0];clock=PchipInterpolator(source,runtime)
 end=3.14 if empty else 3.5;q=np.clip((clock(np.clip(times,2.76,end))-clock(2.76))/(clock(end)-clock(2.76)),0,1)
 # Short smooth acceleration/deceleration, steady angular travel between.
 edge=.18
 def ramp(x):return edge*((x/edge)**3-.5*(x/edge)**4)
 return np.where(q<edge,ramp(q),np.where(q>1-edge,1-edge-ramp(1-q),q-edge/2))/(1-edge)
def solve(w,times,empty,angle=-25.):
 old=w.copy();begin=1.8;full=2.35;release=2.76;end=3.14 if empty else 3.5
 gain=smooth((times-begin)/(full-begin))*(1-smooth((times-release)/(end-release)))
 phase=return_phase(times,empty)
 start=np.argmin(abs(times-release));stop=np.argmin(abs(times-end))
 def pole_data(k,swivel):
  p=old[k];gun=rot(p[ix['WPN_root']]);a,e,t=[p[ix[n],:3,3] for n in ['upperarm_l','lowerarm_l','hand_l']]
  axis=unit(t-a);v=e-a-axis*((e-a)@axis)
  return gun.T@axis,gun.T@R.from_rotvec(axis*np.radians(swivel)).apply(unit(v))
 axis0,pole0=pole_data(start,angle);axis1,pole1=pole_data(stop,0.)
 carried=h.swing(axis0,axis1)@pole0
 pole_angle=np.arctan2(axis1@np.cross(carried,pole1),carried@pole1)
 # Frame the elbow from the full bend, not from a projected world-up hint.
 tau=[];frames=[]
 for k,p in enumerate(w):
  a,e,t=[p[ix[n],:3,3].copy() for n in ['upperarm_l','lowerarm_l','hand_l']]
  axis=unit(t-a);center=a+axis*((e-a)@axis)
  e=center+R.from_rotvec(axis*np.radians(angle)*gain[k]).apply(e-center)
  if release<times[k]<end:
   gun=rot(old[k,ix['WPN_root']]);local_axis=gun.T@axis;q=float(phase[k])
   pole=R.from_rotvec(local_axis*pole_angle*q).apply(h.swing(axis0,local_axis)@pole0)
   e=center+gun@pole*np.linalg.norm(e-center)
  u=e-a;f=t-e;n=unit(np.cross(u,f));dl=frame(f,n)@bind.FL0.T
  tau.append(h.twist_about(dl.T@rot(p[ix['hand_l']])@bind.R[7].T,bind.F0))
  frames.append((a,e,u,f,n,dl))
 tau=np.unwrap(tau);anchor=np.argmin(abs(times-2.55));tau-=np.round(tau[anchor]/(2*np.pi))*2*np.pi
 # Choose the same side of the pronation branch as the existing seated pose.
 if tau[anchor]<0:tau+=2*np.pi
 seat_upper=max(0.,tau[anchor]-np.radians(145))
 release_roll=1-phase
 for k,(a,e,u,f,n,dl) in enumerate(frames):
  if gain[k]<=0:continue
  # Distribute excess roll before the elbow; distal stations carry native
  # V9 half/full forearm pronation without a +/-180 degree branch switch.
  # Release the upper-arm contribution over the whole existing return,
  # rather than snapping it to zero when pronation crosses the cap.
  upper=seat_upper*release_roll[k];fore=tau[k]-upper
  fe=R.from_rotvec(unit(f)*upper).as_matrix()@dl
  up=h.swing(fe@bind.U0,u)@fe
  target=old[k].copy()
  # Include the main upper arm as well as its two skin-bearing helpers.
  target[ix['upperarm_l'],:3,:3]=(up@bind.R[1])*np.linalg.norm(old[k,ix['upperarm_l'],:3,:3],axis=0)
  for j in [2,3]:
   i=arm_ids[j];target[i,:3,:3]=(up@bind.R[j])*np.linalg.norm(old[k,i,:3,:3],axis=0);target[i,:3,3]=a+bind.st[j]*u+up@bind.off[j]
  for j,share in [(4,0),(5,.5),(6,1.)]:
   i=arm_ids[j];D=R.from_rotvec(unit(f)*fore*share).as_matrix()@fe
   target[i,:3,:3]=(D@bind.R[j])*np.linalg.norm(old[k,i,:3,:3],axis=0)
   target[i,:3,3]=e+(bind.st[j]*f+D@bind.off[j] if j!=4 else 0)
  # Elbow translation already fades on the exact IK circle. Orientations
  # fade in their transported frame, so the boundary has no switch.
  olde=old[k,ix['lowerarm_l'],:3,3];oldu=olde-a;oldf=old[k,ix['hand_l'],:3,3]-olde
  for j in range(1,7):
   i=arm_ids[j];axisold=oldu if j<4 else oldf;axisnew=u if j<4 else f
   carried=h.swing(axisold,axisnew)@rot(old[k,i]);wanted=rot(target[i]);delta=R.from_matrix(carried.T@wanted).as_rotvec()
   w[k,i,:3,:3]=(carried@R.from_rotvec(delta*gain[k]).as_matrix())*np.linalg.norm(old[k,i,:3,:3],axis=0)
   if j==1:continue
   if j==4:w[k,i,:3,3]=e
   else:
    # Auxiliary stations stay on the same segment with their rest offset.
    origin=a if j<4 else e;axis=u if j<4 else f;D=rot(w[k,i])@bind.R[j].T
    w[k,i,:3,3]=origin+bind.st[j]*axis+D@bind.off[j]
 # The original main upper-arm roll contains a rapid early-return correction.
 # Transport the seated and recovered bone frames directly, rather than
 # fading that old intermediate roll back into the corrected elbow path.
 def anatomical(p,upper):
  a,e,t=[p[ix[n],:3,3]for n in ['upperarm_l','lowerarm_l','hand_l']]
  u=e-a;f=t-e;n=unit(np.cross(u,f))
  return frame(u,n)@bind.FU0.T if upper else frame(f,n)@bind.FL0.T
 seated=w[start].copy();goal=old[stop].copy()
 endpoints={j:(R.from_matrix(anatomical(seated,j<4).T@rot(seated[arm_ids[j]])@bind.R[j].T),R.from_matrix(anatomical(goal,j<4).T@rot(goal[arm_ids[j]])@bind.R[j].T))for j in [1,2,3,4]}
 for k in range(start+1,stop):
  q=float(phase[k]);a,e,t=[w[k,ix[n],:3,3]for n in ['upperarm_l','lowerarm_l','hand_l']];u=e-a;f=t-e
  for j,(q0,q1)in endpoints.items():
   D=anatomical(w[k],j<4)@(q0*R.from_rotvec((q0.inv()*q1).as_rotvec()*q)).as_matrix();i=arm_ids[j]
   w[k,i,:3,:3]=(D@bind.R[j])*np.linalg.norm(old[k,i,:3,:3],axis=0)
   if j in [2,3]:w[k,i,:3,3]=a+bind.st[j]*u+D@bind.off[j]
  fe=rot(w[k,arm_ids[4]])@bind.R[4].T;roll=h.twist_about(fe.T@rot(w[k,ix['hand_l']])@bind.R[7].T,bind.F0)
  roll=(roll+np.pi)%(2*np.pi)-np.pi
  for j,share in [(5,.5),(6,1.)]:
   D=fe@R.from_rotvec(unit(bind.F0)*roll*share).as_matrix();i=arm_ids[j]
   # Match the exact existing recovered helper orientation at the endpoint.
   fg=rot(goal[arm_ids[4]])@bind.R[4].T;rg=h.twist_about(fg.T@rot(goal[ix['hand_l']])@bind.R[7].T,bind.F0);rg=(rg+np.pi)%(2*np.pi)-np.pi
   nominal=fg@R.from_rotvec(unit(bind.F0)*rg*share).as_matrix();extra=R.from_matrix(nominal.T@rot(goal[i])@bind.R[j].T)
   D=D@R.from_rotvec(extra.as_rotvec()*q).as_matrix();w[k,i,:3,:3]=(D@bind.R[j])*np.linalg.norm(old[k,i,:3,:3],axis=0);w[k,i,:3,3]=e+bind.st[j]*f+D@bind.off[j]
 return w,gain
for path,c in d['clips'].items():
 if '/SideMagazine' not in path:continue
 t=np.array(c['times']);raw=np.array(c['frames']);empty=path.endswith('_empty')
 for family in d['profiles']:
  w=world(layer(raw,path,family,t));after,gain=solve(w.copy(),t,empty)
  output[(path,family)]=dict(times=t,before=w,after=after,gain=gain)
  report[family+'/'+path.split('.')[-1]]=dict(max_elbow_cm=float(np.linalg.norm(after[:,ix['lowerarm_l'],:3,3]-w[:,ix['lowerarm_l'],:3,3],axis=1).max()),hand_difference=float(np.abs(after[:,ix['hand_l']]-w[:,ix['hand_l']]).max()))
  print(family,path.split('.')[-1],report[family+'/'+path.split('.')[-1]],flush=True)
pickle.dump(output,open(r/'candidate.pkl','wb'));(r/'candidate.json').write_text(json.dumps(report,indent=2))
