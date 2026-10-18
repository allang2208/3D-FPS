"""Fit Sparrow's upper-body takes to the actual bow and Jason hand anatomy."""
import gzip,json,sys
import numpy as np
from bow_math import *

d=read('retargeted.json.gz');e=read('equipment.json.gz');contact=Contacts(d,e)
correction_path=O/'contact-correction.json'
contact_delta=np.array(json.loads(correction_path.read_text())['delta_in_right_hand_cm']) if correction_path.exists() else np.zeros(3)
names,parents=d['names'],d['parents'];ix=contact.ix
neutral=np.asarray(d['neutral']['frames'][0]);ref=np.asarray(d['reference'])
def child(b,ancestor):
 while b>=0:
  if b==ancestor:return True
  b=parents[b]
 return False
upper=np.array([child(i,ix['spine_01']) for i in range(len(names))])
segments={}
for side in ('l','r'):
 a,b,h=[ix[n+'_'+side] for n in ('upperarm','lowerarm','hand')]
 segments[side]=[3 if child(i,h) else 2 if child(i,b) else 1 if child(i,a) else 0 for i in range(len(names))]
def donor(role,t):
 f=sample(d['clips'][role],t);source=fk(f,parents);base=fk(neutral,parents)
 hip=ix['pelvis'];offset=base[hip,:3]-source[hip,:3]
 correction=mul(base[hip,3:7],inv(source[hip,3:7]))
 # Keep Sparrow's actual chest/shoulder directions after removing root travel.
 # Dropping the donor's pelvis turn outright would demand a 60-degree wrist
 # correction. Spread that turn through the lumbar spine instead of the hand.
 out=base.copy();spines=[ix[f'spine_{i:02d}'] for i in range(1,6)]
 rotations={b:slerp(correction,np.array([0.,0,0,1]),(i+1)/5.) for i,b in enumerate(spines)}
 for i in range(len(names)):
  if not upper[i]:continue
  ancestor=i
  while ancestor not in rotations:ancestor=parents[ancestor]
  q=rotations[ancestor];pivot=source[ancestor,:3]
  out[i,:3]=pivot+offset+rot(q,source[i,:3]-pivot)
  out[i,3:7]=unit(mul(q,source[i,3:7]));out[i,7:]=source[i,7:]
 return local(out,parents)

# Preserve the existing physical bow mount and native-body grip, including
# the thumb. Sparrow provides the torso/elbow performance, not foreign binds.
native_hold=contact.native_pose('Hold',0)
grip,nock_frame=contact.frames(native_hold)
hold_source=donor('RMB_Loop',0);hw=fk(hold_source,parents)
hold_bow=compose(hw[ix['hand_l'],:7],grip)
forward=np.array([0.,1.,0.]);up=rot(hold_bow[3:7],[0.,0.,1.])
up=unit(up-forward*np.dot(up,forward))
# Keep Sparrow's bow cant. Forcing a vertical bow would put an unnecessary
# sixty-degree roll through the wrist; only align the shooting direction.
aim=R.from_matrix(np.column_stack((forward,np.cross(up,forward),up))).as_quat()
bow_rotation_correction=mul(aim,inv(hold_bow[3:7]))

def pair_fit(w,left,right):
 targets={'l':left.copy(),'r':right.copy()};centres={};radii={}
 for side in ('l','r'):
  a,b,h=[w[ix[n+'_'+side],:3] for n in ('upperarm','lowerarm','hand')]
  centres[side]=a-targets[side][:3];radii[side]=.975*(np.linalg.norm(a-b)+np.linalg.norm(b-h))
 def inside(p,s):return np.linalg.norm(p-centres[s])<=radii[s]+1e-7
 z=np.zeros(3)
 if inside(z,'l') and inside(z,'r'):return targets
 candidates=[]
 for s,o in [('l','r'),('r','l')]:
  delta=-centres[s];p=centres[s]+unit(delta)*min(np.linalg.norm(delta),radii[s])
  if inside(p,o):candidates.append(p)
 if candidates:shift=min(candidates,key=lambda p:np.dot(p,p))
 else:
  delta=centres['r']-centres['l'];distance=np.linalg.norm(delta)
  if not abs(radii['l']-radii['r'])<distance<sum(radii.values()):
   raise RuntimeError('The two bow contacts exceed native arm reach')
  axis=delta/distance;along=(radii['l']**2-radii['r']**2+distance**2)/(2*distance)
  centre=centres['l']+axis*along;radius=np.sqrt(max(0,radii['l']**2-along**2))
  toward=-centre+axis*np.dot(centre,axis)
  if np.linalg.norm(toward)<1e-7:toward=np.cross(axis,[0,0,1])
  shift=centre+unit(toward)*radius
 for target in targets.values():target[:3]+=shift
 return targets

current_clip=''
roll_history={}
def fit_arm(f,side,target,pass_name='contact'):
 w=fk(f,parents);old=w.copy();a,b,h=[ix[n+'_'+side] for n in ('upperarm','lowerarm','hand')]
 shoulder,elbow,hand=old[a,:3],old[b,:3],old[h,:3]
 l1=np.linalg.norm(elbow-shoulder);l2=np.linalg.norm(hand-elbow)
 axis=unit(target[:3]-shoulder);distance=np.linalg.norm(target[:3]-shoulder)
 if distance>=l1+l2:raise RuntimeError('Unreachable authored wrist')
 bend=elbow-shoulder-axis*np.dot(elbow-shoulder,axis)
 if current_clip=='Release' and side=='l':
  # The bow-support arm is nearly extended. Use its fitted hold/carry elbow
  # plane during lowering instead of a nearly singular donor projection.
  lower=smooth((release_progress-.24)/.76)
  direction=(held_w[b,:3]-held_w[a,:3])*(1-lower)+(carry_w[b,:3]-carry_w[a,:3])*lower
  bend=direction-axis*np.dot(direction,axis)
 if np.linalg.norm(bend)<.15:
  pole=np.array([1 if side=='l' else -1,0,-.2]);bend=pole-axis*np.dot(pole,axis)
 bend=unit(bend);along=(l1*l1-l2*l2+distance*distance)/(2*distance)
 joint=shoulder+axis*along+bend*np.sqrt(max(0,l1*l1-along*along))
 uq=between(elbow-shoulder,joint-shoulder);lq=between(hand-elbow,target[:3]-joint)
 # Spread palm roll through the forearm and its weighted helpers; keep the
 # authored elbow bend plane and avoid putting all twist into the wrist.
 provisional=mul(lq,old[b,3:7]);wanted=mul(target[3:7],inv(mul(inv(old[b,3:7]),old[h,3:7])))
 delta=mul(wanted,inv(provisional));axis=unit(target[:3]-joint)
 twist=np.r_[axis*np.dot(delta[:3],axis),delta[3]]
 if np.linalg.norm(twist)>1e-7:
  if current_clip=='Release':
   # Preserve signed roll across 180 degrees before distributing it. A
   # shortest-path quaternion blend switches branches at that crossing.
   angle=2*np.arctan2(np.dot(twist[:3],axis),twist[3]);key=(side,pass_name)
   if key in roll_history:angle+=2*np.pi*round((roll_history[key]-angle)/(2*np.pi))
   roll_history[key]=angle;lq=mul(R.from_rotvec(axis*angle*.65).as_quat(),lq)
  else:lq=mul(slerp(np.array([0.,0,0,1]),unit(twist),.65),lq)
 hq=mul(target[3:7],inv(old[h,3:7]))
 for i,segment in enumerate(segments[side]):
  if segment==1:q,p,new=uq,shoulder,shoulder
  elif segment==2:q,p,new=lq,elbow,joint
  elif segment==3:q,p,new=hq,hand,target[:3]
  else:continue
  w[i,:3]=new+rot(q,old[i,:3]-p);w[i,3:7]=unit(mul(q,old[i,3:7]))
 return local(w,parents)

def make(f,native,contacting=True,free_right=None):
 w=fk(f,parents);g,n=contact.frames(native)
 left=w[ix['hand_l'],:7].copy();left[3:7]=unit(mul(bow_rotation_correction,left[3:7]))
 bow_frame=compose(left,g)
 right_in_bow=compose(inverse(native[contact.ei['bow_grip'],:7]),
     compose(native[contact.ei['hand_r'],:7],inverse(contact.mounts['r'])))
 right=compose(bow_frame,right_in_bow) if contacting else w[ix['hand_r'],:7].copy()
 if contacting:right[:3]-=rot(right[3:7],contact_delta)
 n[:3]+=contact_delta
 if free_right is not None:right=free_right
 targets=pair_fit(w,left,right)
 for side in ('l','r'):f=fit_arm(f,side,targets[side])
 for side in ('l','r'):
  fingers=contact.fingers(native,side)
  for i,segment in enumerate(segments[side]):
   if segment==3 and i!=ix['hand_'+side]:f[i]=fingers[i]
 curves={}
 for j,k in enumerate(('X','Y','Z','QX','QY','QZ','QW')):curves['SparrowBowGrip'+k]=float(g[j])
 for j,k in enumerate(('X','Y','Z')):curves['SparrowBowNock'+k]=float(n[j])
 return f,curves

release_only='--release-only' in sys.argv
clips=read('authored.json.gz')['clips'] if release_only else {}
rate=30
def collect(label,duration,fn,source,source_range):
 global current_clip
 if release_only and label!='Release':return
 current_clip=label;roll_history.clear()
 frames=[];curves={};count=max(1,round(duration*rate))
 for i in range(count+1):
  f,c=fn(i/count,i/rate)
  if not np.isfinite(f).all():raise RuntimeError('Non-finite authored pose')
  frames.append(f.tolist())
  for key,value in c.items():curves.setdefault(key,[]).append(value)
 clips[label]=dict(rate=rate,frames=frames,float_curves=curves,source=source,source_range=source_range)
 print('SPARROW_AUTHORED',label,len(frames),flush=True)

carry_role='Travel_Mode_Idle_BowDown'
carry_length=d['clips'][carry_role]['duration']
collect('Carry',round(carry_length*rate)/rate,
 lambda p,t:make(donor(carry_role,p*carry_length),contact.native_pose('Idle',p),False),
 d['clips'][carry_role]['asset'],[0,carry_length])
carry=np.asarray(clips['Carry']['frames'][0])
carry_w=fk(carry,parents)
draw_length=d['clips']['RMB_Drawback']['duration']
collect('Draw',round(draw_length*rate)/rate,
 lambda p,t:make(donor('RMB_Drawback',p*draw_length),contact.native_pose('Draw',p)),
 d['clips']['RMB_Drawback']['asset'],[0,draw_length])
collect('Ready',1/30,lambda p,t:(np.asarray(clips['Draw']['frames'][0]),{k:v[0] for k,v in clips['Draw']['float_curves'].items()}),d['clips']['RMB_Drawback']['asset'],[0,0])
hold_length=d['clips']['RMB_Loop']['duration']
collect('Hold',round(hold_length*rate)/rate,
 lambda p,t:make(donor('RMB_Loop',p*hold_length),contact.native_pose('Hold',p)),
 d['clips']['RMB_Loop']['asset'],[0,hold_length])
held=np.asarray(clips['Hold']['frames'][0]);held_w=fk(held,parents)
source_held_w=fk(hold_source,parents)
def release(p,t):
 global release_progress
 release_progress=p
 # Use Sparrow's release/follow-through, then lower into its existing carry.
 # The original take re-nocks; that later action is owned by the game clock.
 source=donor('RMB_Fire',p*.65);w=fk(source,parents)
 right=held_w[ix['hand_r'],:7].copy()
 right[:3]+=w[ix['hand_r'],:3]-source_held_w[ix['hand_r'],:3]
 right[3:7]=unit(mul(mul(w[ix['hand_r'],3:7],inv(source_held_w[ix['hand_r'],3:7])),right[3:7]))
 f,c=make(source,contact.native_pose('Release',p),False,right)
 # Free fingers have no string target. The contact IK became singular as
 # they opened; release smoothly between two fitted native finger poses.
 finger_release=smooth(p/.28)
 for side in ('l','r'):
  for i,segment in enumerate(segments[side]):
   if segment==3 and i!=ix['hand_'+side]:
    f[i]=blend(held[i:i+1],carry[i:i+1],finger_release if side=='r' else 0.)[0]
 lower=smooth((p-.24)/.76)
 f=blend(f,carry,lower)
 # Arc the released hand outside the chest on its way down.
 fw=fk(f,parents);free=fw[ix['hand_r'],:7].copy()
 free[:3]+=np.array([-7.,6.,0.])*np.sin(np.pi*lower)
 targets=pair_fit(fw,fw[ix['hand_l'],:7],free)
 for side in ('l','r'):f=fit_arm(f,side,targets[side],'lowering')
 return f,c
collect('Release',.6666666667,release,d['clips']['RMB_Fire']['asset'],[0,.65])

result=dict(mesh=d['mesh'],names=names,parents=parents,clips=clips,
 source_url='https://www.fab.com/listings/7d76ddf0-d9ce-4d00-939e-d72793534d01',
 provenance='Epic Games Paragon Sparrow; Jason-native contact adaptation',
 authoring_script='SourceAssets/BowSparrowThirdPerson20261018/author.py')
with gzip.open(O/'authored.json.gz','wt',encoding='utf-8') as f:json.dump(result,f,separators=(',',':'))
(O/'authoring.json').write_text(json.dumps({'clips':{k:len(v['frames']) for k,v in clips.items()},
 'bow_mount_in_native_left_hand':grip.tolist(),'string_marker_in_native_right_hand':nock_frame.tolist(),
 'hold_bow_rotation_correction_degrees':R.from_quat(bow_rotation_correction).magnitude()*180/np.pi,
 'cancel_draw':'Sample the fitted Draw in reverse from current draw fraction; no duplicate reverse clip.',
 'game_run':False},indent=2))
print('SPARROW_BOW_AUTHORING_SAVED',flush=True)
