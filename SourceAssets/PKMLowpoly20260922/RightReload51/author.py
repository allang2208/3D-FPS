"""Video-directed PKM right-arm refinement from current native animation tracks."""
from pathlib import Path
import json,numpy as np
from scipy.spatial.transform import Rotation as R,Slerp
from scipy.ndimage import gaussian_filter1d
P=Path(__file__).resolve().parent;O=P/'Authored';O.mkdir(exist_ok=True)
bare=json.loads((P/'Inputs/bare.json').read_text());bones=bare['bones'];indices={v['index']:n for n,v in bones.items()};parent={n:indices.get(v['parent']) for n,v in bones.items()}
def mat(t):
 m=np.eye(4);m[:3,:3]=R.from_quat(t['q']).as_matrix()*np.array(t['s']);m[:3,3]=t['p'];return m
def unit(x):return x/max(np.linalg.norm(x),1e-10)
def smooth(x):
 x=np.clip(x,0,1);return x*x*x*(x*(x*6-15)+10)
def ramp(t,a,b):return smooth((t-a)/(b-a))
def swing(a,b):
 a=unit(a);b=unit(b);q=np.r_[np.cross(a,b),1+np.clip(a@b,-1,1)]
 if np.linalg.norm(q)<1e-7:return R.from_rotvec(unit(np.cross(a,[0,0,1]))*np.pi).as_matrix()
 return R.from_quat(unit(q)).as_matrix()
def basis(a,b):
 a=unit(a);b=unit(b-a*(b@a));return np.column_stack((a,b,np.cross(a,b)))
def mixrot(a,b,w):return a@R.from_rotvec(R.from_matrix(a.T@b).as_rotvec()*w).as_matrix()
def pack(m,previous=None):
 scale=np.linalg.norm(m[:3,:3],axis=0);q=R.from_matrix(m[:3,:3]/scale).as_quat()
 if previous is not None and q@previous<0:q=-q
 return dict(p=m[:3,3].tolist(),q=q.tolist(),s=scale.tolist())
rest={n:mat(v) for n,v in bones.items()};refrot={n:R.from_quat(v['q']).as_matrix() for n,v in bones.items()}
S0,E0,H0=[rest[n][:3,3] for n in ['upperarm_r','lowerarm_r','hand_r']];U0=E0-S0;F0=H0-E0;width=rest['index_metacarpal_r'][:3,3]-rest['pinky_metacarpal_r'][:3,3];bind=basis(F0,width)
changed=['upperarm_r','upperarm_twist_01_r','upperarm_twist_02_r','lowerarm_r','lowerarm_twist_02_r','lowerarm_twist_01_r','hand_r','PKM_Charge']
fingers=[n for n in bones if n.endswith('_r') and n.startswith(('thumb_','index_','middle_','ring_','pinky_'))]
# Keep every descendant's original local channels; only these eight native tracks are replaced.
report={}
for family in ['base','vertical','canted','prism','angled']:
 clip=json.loads((P/'Inputs'/f'{family}.json').read_text());rows=clip['frames'];fps=(len(rows)-1)/clip['duration'];worlds=[{n:mat(v) for n,v in row.items()} for row in rows]
 contact=worlds[round(5.13*fps)];skin={n:contact[n]@np.linalg.inv(rest[n]) for n in bones};pads=[]
 for digit in ['index','middle']:
  candidates=[]
  for point,ws in zip(bare['positions'],bare['weights']):
   if ws.get(digit+'_02_r',0)<.5:continue
   h=np.r_[point,1.];v=sum(w*(skin[n]@h)[:3] for n,w in ws.items());candidates.append(v)
  target=contact['PKM_Charge'][:3,3];pads.extend(sorted(candidates,key=lambda v:np.linalg.norm(v-target))[:8])
 anchor=(np.linalg.inv(contact['hand_r'])@np.r_[np.mean(pads,axis=0),1])[:3]
 home=np.linalg.inv(contact['WPN_root'])@contact['PKM_Charge'];rear=worlds[round(5.36*fps)];travel=(np.linalg.inv(rear['WPN_root'])@rear['PKM_Charge'])[:3,3]-home[:3,3]
 handtargets=[];charge_targets=[];circles=[];phases=[];preferred=[];pole_frames=[];lastaxis=None
 for i,original in enumerate(worlds):
  t=i/fps;H=original['hand_r'].copy();charge=original['PKM_Charge'].copy()
  weight=ramp(t,3.90,4.25)*(1-ramp(t,6.02,6.30))
  if 5.13<=t<=5.82:
   fraction=(ramp(t,5.13,5.36)**1.22)*(1-ramp(t,5.48,5.82)**.82)
   charge[:3,3]=(original['WPN_root']@np.r_[home[:3,3]+travel*fraction,1])[:3]
   H[:3,3]+=charge[:3,3]-original['PKM_Charge'][:3,3]
  # Roll around the actual native finger-pad anchor, so the hand stays on the lug.
  roll=-8*ramp(t,5.13,5.36)+14*ramp(t,5.48,5.78)-6*ramp(t,5.82,5.98)
  roll*=ramp(t,5.02,5.13)*(1-ramp(t,5.98,6.08))
  axis=unit(H[:3,:3]@refrot['hand_r'].T@width);pivot=(H@np.r_[anchor,1])[:3];delta=R.from_rotvec(axis*np.radians(roll)).as_matrix()
  H[:3,:3]=delta@H[:3,:3];H[:3,3]=pivot+delta@(H[:3,3]-pivot)
  handtargets.append(H);charge_targets.append(charge)
  S=original['upperarm_r'][:3,3];E=original['lowerarm_r'][:3,3];W=H[:3,3];a=np.linalg.norm(E-S);b=np.linalg.norm(original['hand_r'][:3,3]-E);axis=unit(W-S);dist=np.linalg.norm(W-S)
  along=(a*a-b*b+dist*dist)/(2*dist);center=S+axis*along;radius=np.sqrt(max(0,a*a-along*along));radial=unit(E-center-axis*((E-center)@axis))*radius
  x=unit(radial) if lastaxis is None else swing(lastaxis,axis)@pole_frames[-1][0];y=np.cross(axis,x);lastaxis=axis;pole_frames.append((x,y))
  phase=np.arctan2(radial@y,radial@x);phases.append(phase)
  hrot=H[:3,:3]/np.linalg.norm(H[:3,:3],axis=0);aim=hrot@refrot['hand_r'].T@unit(F0)
  target=W-aim*b-center;target-=axis*(target@axis)
  phi=np.arctan2(axis@np.cross(unit(radial),unit(target)),unit(radial)@unit(target)) if np.linalg.norm(target)>1e-6 else 0
  # Limited pole participation; never rotate a whole revolution to chase the palm.
  phi=np.clip(phi,-np.radians(65),np.radians(65))*.8*weight
  preferred.append(phi);circles.append((center,axis,radial,radius,weight))
 phases=np.unwrap(phases);pole=gaussian_filter1d(phases+np.array(preferred),fps*.035,mode='nearest')
 tracks={n:[] for n in changed};previous={n:None for n in changed};result=[]
 for i,original in enumerate(worlds):
  t=i/fps;p={n:m.copy() for n,m in original.items()};center,axis,radial,radius,weight=circles[i]
  H=handtargets[i];S=p['upperarm_r'][:3,3].copy();oldE=p['lowerarm_r'][:3,3].copy();W=H[:3,3]
  if weight>0:
   phase=phases[i]+(pole[i]-phases[i])*weight;x,y=pole_frames[i];E=center+radius*(x*np.cos(phase)+y*np.sin(phase))
   handdelta=(H[:3,:3]/np.linalg.norm(H[:3,:3],axis=0))@refrot['hand_r'].T
   fore=basis(W-E,handdelta@width)@bind.T
   upper=swing(fore@U0,E-S)@fore
   # All skinning helpers use the same complete segment transform. This removes
   # the old disagreement between upperarm, elbow and partial twist helpers.
   for names,origin,restorigin,restaxis,newaxis,skinrot in [
    (['upperarm_r','upperarm_twist_01_r','upperarm_twist_02_r'],S,S0,U0,E-S,upper),
    (['lowerarm_r','lowerarm_twist_02_r','lowerarm_twist_01_r'],E,E0,F0,W-E,fore)]:
    for n in names:
     station=(rest[n][:3,3]-restorigin)@restaxis/(restaxis@restaxis);offset=rest[n][:3,3]-restorigin-station*restaxis
     targetrot=skinrot@refrot[n];oldrot=original[n][:3,:3]/np.linalg.norm(original[n][:3,:3],axis=0)
     # Swing the source segment to the new pole before easing its axial roll.
     beforeaxis=(oldE-S) if names[0]=='upperarm_r' else (original['hand_r'][:3,3]-oldE)
     carried=swing(beforeaxis,newaxis)@oldrot
     p[n][:3,:3]=mixrot(carried,targetrot,weight)*np.linalg.norm(original[n][:3,:3],axis=0)
     p[n][:3,3]=origin+station*newaxis+mixrot(swing(beforeaxis,newaxis)@(oldrot@refrot[n].T),skinrot,weight)@offset
   p['hand_r']=H;p['PKM_Charge']=charge_targets[i]
   D=H@np.linalg.inv(original['hand_r'])
   for n in fingers:p[n]=D@original[n]
  for n in changed:
   key=pack(np.linalg.inv(p[parent[n]])@p[n],previous[n]);previous[n]=np.array(key['q']);tracks[n].append(key)
  if family=='base':result.append({n:pack(m) for n,m in p.items()})
 data=dict(asset=clip['asset'],source_sha256=clip['source_sha256'],keys=len(rows),duration=clip['duration'],tracks=tracks,revision='RightReload51')
 (O/(family+'.json')).write_text(json.dumps(data,separators=(',',':')))
 if family=='base':(O/'base_world.json').write_text(json.dumps(result,separators=(',',':')))
 report[family]=dict(source=clip['asset'],keys=len(rows),modified_tracks=changed,window=[3.9,6.3],duration=clip['duration'],contact_clock=[4.82,5.13,5.36,5.48,5.82],pad_anchor=anchor.tolist(),handle_travel_cm=float(np.linalg.norm(travel)))
 print('PKM51_AUTHORED',family,flush=True)
(P/'authoring.json').write_text(json.dumps(report,indent=2))
