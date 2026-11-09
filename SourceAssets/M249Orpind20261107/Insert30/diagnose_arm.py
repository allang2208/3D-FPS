from common import *
import json
h=s['hinge'];report={}
for path,c in d['clips'].items():
 if '/SideMagazine' not in path:continue
 times=np.array(c['times']);w=world(layer(np.array(c['frames']),path,'base',times));out=[]
 for tm in [1.8,2,2.2,2.3,2.5,2.55,2.70,2.76,2.80,2.85,2.9,2.95,3.,3.05,3.10,3.14,3.3,3.5]:
  k=np.argmin(abs(times-tm));p=w[k];a,e,t=[p[ix[n],:3,3] for n in ['upperarm_l','lowerarm_l','hand_l']];axis=unit(t-a);center=a+axis*((e-a)@axis)
  options=[]
  for deg in [-60,-40,-20,0,20,40,60]:
   E=center+R.from_rotvec(axis*np.radians(deg)).apply(e-center);u=E-a;f=t-E;n=unit(np.cross(u,f));dl=frame(f,n)@bind.FL0.T;du=frame(u,n)@bind.FU0.T
   tau=h.twist_about(dl.T@rot(p[ix['hand_l']])@bind.R[7].T,bind.F0);tau=(np.degrees(tau)+180)%360-180
   options.append([deg,*np.round(E,2),round(tau,2)])
  old=[]
  u=e-a;f=t-e;n=unit(np.cross(u,f));dl=frame(f,n)@bind.FL0.T;du=frame(u,n)@bind.FU0.T
  for j in [1,2,3,4,5,6]:
   D=du if j<4 else dl;axis0=bind.U0 if j<4 else bind.F0
   old.append(round(float((np.degrees(h.twist_about(D.T@rot(p[arm_ids[j]])@bind.R[j].T,axis0))+180)%360-180),1))
  out.append(dict(source=float(times[k]),options=options,rolls=old))
  if 2.3<=tm<=2.9:print(path.split('.')[-1],tm,'rolls',old,'elbow candidates',options,flush=True)
 report[path]=out
(r/'arm_diagnosis.json').write_text(json.dumps(report,indent=2))
