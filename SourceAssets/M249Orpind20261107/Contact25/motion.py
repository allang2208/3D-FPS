"""Small contact edits with fixed arm lengths and unchanged right/mechanical tracks."""
from pathlib import Path
import numpy as np,pickle,json,sys
from scipy.spatial.transform import Rotation as R
r=Path(__file__).resolve().parent;helper=r.parent/'Repair20/author.py';s={'__file__':str(helper)}
exec(compile(helper.read_text().split("outdir=r/'Motion'")[0],str(helper),'exec'),s)
d=pickle.load(open(r/'current.pkl','rb'));s['d']=d
world,layer,encode,ease,rot,unit=[s[k] for k in ['world','layer','encode','ease','rot','unit']]
names,parents,ix=s['names'],s['parents'],s['ix'];hinge=s['hinge'];bind,arm_names=s['binding']('l');arm_ids=[ix[n] for n in arm_names]
fingers=[i for i,n in enumerate(names) if n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky'))]
left_ids=arm_ids+fingers+[ix['ik_hand_l']];params=json.loads((r/'parameters.json').read_text())
def rigid(m):
 a=m.copy();a[:3,:3]=rot(m);return a
def correct(w,x,arm=True):
 old=w;gun=rigid(w[ix['WPN_root']]);v=np.linalg.inv(gun)@w
 local={i:np.linalg.inv(v[parents[i]])@v[i] for i in fingers}
 v[ix['hand_l'],:3,3]+=x[:3]
 rr=np.eye(3)
 for j in range(3):rr=rr@R.from_rotvec(np.eye(3)[j]*np.radians(x[3+j])).as_matrix()
 v[ix['hand_l'],:3,:3]=rr@v[ix['hand_l'],:3,:3]
 for value,p in zip(x[6:],params):
  i=ix[p['bone']];local[i][:3,:3]=local[i][:3,:3]@R.from_rotvec(np.array(p['axis'])*np.radians(value)).as_matrix()
 for i in fingers:v[i]=v[parents[i]]@local[i]
 v[ix['ik_hand_l']]=v[ix['hand_l']]
 new=old.copy();moving=[ix['hand_l']]+fingers+[ix['ik_hand_l']];new[moving]=gun@v[moving]
 if not arm or np.linalg.norm(x[:6])<1e-9:return new
 a,e,h=[old[ix[n],:3,3] for n in ['upperarm_l','lowerarm_l','hand_l']];target=new[ix['hand_l'],:3,3]
 upper=np.linalg.norm(e-a);lower=np.linalg.norm(h-e);axis0=unit(h-a);axis=unit(target-a);length=np.linalg.norm(target-a)
 if length>=upper+lower-.01:raise RuntimeError('Contact correction exceeds original arm reach')
 pole=unit(e-a-axis0*((e-a)@axis0));pole=hinge.swing(axis0,axis)@pole
 along=(upper*upper-lower*lower+length*length)/(2*length);elbow=a+axis*along+pole*np.sqrt(max(0.,upper*upper-along*along))
 du=hinge.swing(e-a,elbow-a);df=hinge.swing(h-e,target-elbow)
 for n in ['upperarm_l','upperarm_twist_01_l','upperarm_twist_02_l']:
  i=ix[n];new[i,:3,:3]=du@old[i,:3,:3];new[i,:3,3]=a+du@(old[i,:3,3]-a)
 residual=rot(new[ix['hand_l']])@rot(old[ix['hand_l']]).T@df.T;quat=R.from_matrix(residual).as_quat();axisf=unit(target-elbow)
 angle=2*np.arctan2(quat[:3]@axisf,quat[3]);angle=(angle+np.pi)%(2*np.pi)-np.pi
 for n,share in [('lowerarm_l',0.),('lowerarm_twist_02_l',.5),('lowerarm_twist_01_l',1.)]:
  i=ix[n];turn=R.from_rotvec(axisf*angle*share).as_matrix()@df;new[i,:3,:3]=turn@old[i,:3,:3];new[i,:3,3]=elbow+turn@(old[i,:3,3]-e)
 return new

if __name__=='__main__':
 fits=pickle.load(open(r/'idle_fit.pkl','rb'));poses=pickle.load(open(r/'poses.pkl','rb'));out=pickle.load(open(r/'corrected.pkl','rb')) if (r/'corrected.pkl').exists() else {};stats={};wanted=sys.argv[1:]
 idle_path=next(p for p in d['clips'] if p.endswith('_idle'))
 for family in d['profiles']:
  if wanted and family not in wanted:continue
  if family!='base':
   ref=fits[family]['old_world'];refhand=np.linalg.inv(rigid(ref[ix['WPN_root']]))@ref[ix['hand_l']];xidle=fits[family]['parameters'];goal=fits[family]['new_world'];goal=np.linalg.inv(rigid(goal[ix['WPN_root']]))@goal;goal_local={i:np.linalg.inv(goal[parents[i]])@goal[i] for i in fingers}
  for path,c in d['clips'].items():
   side='/SideMagazine' in path
   if family=='base' and not side:continue
   times=np.array(c['times']);old=world(layer(np.array(c['frames']),path,family,times));new=old.copy();weights=[]
   for k,tm in enumerate(times):
    weight=0.
    if family!='base':
     hand=np.linalg.inv(rigid(old[k,ix['WPN_root']]))@old[k,ix['hand_l']]
     distance=np.linalg.norm(hand[:3,3]-refhand[:3,3]);angle=np.degrees(np.linalg.norm(R.from_matrix(rot(hand)@rot(refhand).T).as_rotvec()))
     weight=float((1-ease((distance-.5)/3.5))*(1-ease((angle-4)/28)))
     if side and tm>2.76:
      end=3.14 if path.split('.')[0].endswith('_empty') else 3.50
      q=np.clip((tm-2.76)/(end-2.76),0,1);weight=float(ease((q-.35)/.65))
     if path==idle_path:weight=1.
     if weight>1e-9:new[k]=correct(old[k],xidle*weight)
     if side and 2.76<tm<end:
      # Finish turning and shaping the palm while it is still outside the
      # mounted grip. Late anatomical-frame rotation otherwise drags fingers
      # through the handle during the last centimetres of an approach.
      ready=float(ease((q-(.4 if family=='angled' else .45))/(.3 if family=='angled' else .33)));gun=rigid(new[k,ix['WPN_root']]);desired=gun@goal[ix['hand_l']]
      if family=='angled':
       align=float(ease((q-.5)/.2));hand_local=np.linalg.inv(gun)@new[k,ix['hand_l']];seat=np.zeros(6+len(params));seat[1:3]=(goal[ix['hand_l'],1:3,3]-hand_local[1:3,3])*align;new[k]=correct(new[k],seat)
      delta=R.from_matrix(rot(desired)@rot(new[k,ix['hand_l']]).T);turn=R.from_rotvec(delta.as_rotvec()*ready).as_matrix();localturn=gun[:3,:3].T@turn@gun[:3,:3];xx=np.zeros(6+len(params));xx[3:6]=R.from_matrix(localturn).as_euler('XYZ',degrees=True);new[k]=correct(new[k],xx)
      local={i:np.linalg.inv(new[k,parents[i]])@new[k,i] for i in fingers}
      close=float(ease((q-.82)/.18))
      for i in fingers:
       # Approach the handle with open fingers; curling a closed fist around
       # a handle before the palm seats sweeps the fingertips through it.
       target=goal_local[i].copy();n=names[i]
       if 'metacarpal' not in n and not n.startswith('thumb') and not (family=='angled' and (n.startswith('pinky') or '_01_' in n)):
        rest=np.linalg.inv(s['B'][parents[i]])@s['B'][i];opened=target.copy();opened[:3,:3]=s['mix'](target,rest,.70)[:3,:3];target=s['mix'](opened,target,close)
       new[k,i]=new[k,parents[i]]@s['mix'](local[i],target,ready)
    weights.append(weight)
   out[(family,path)]=dict(old=old,world=new,times=times,weights=np.array(weights));stats[family+'/'+path.split('/')[-1]]=dict(affected_frames=int(np.sum(np.array(weights)>0)),frames=len(times))
   print('CONTACT25_HOLD',family,path.split('/')[-1],stats[family+'/'+path.split('/')[-1]],flush=True)
 pickle.dump(out,open(r/'corrected.pkl','wb'));(r/'holding.json').write_text(json.dumps(stats,indent=2))
