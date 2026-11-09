"""Camera-clear shoulders and semantic foregrip handoff, using saved Repair20 poses."""
from pathlib import Path
import pickle,json,gzip,numpy as np,sys
from scipy.spatial.transform import Rotation as R,Slerp
from scipy.optimize import minimize_scalar
from scipy.interpolate import PchipInterpolator
r=Path(__file__).resolve().parent;prev=r.parent/'Repair20'
scope={'__file__':str(prev/'author.py')};exec(compile((prev/'author.py').read_text().split("outdir=r/'Motion'")[0],str(prev/'author.py'),'exec'),scope)
rot,unit,frame,mix,ease,encode,binding,hinge=[scope[k] for k in ['rot','unit','frame','mix','ease','encode','binding','hinge']]
d=pickle.load(open(prev/'saved_compressed.pkl','rb'));cache=pickle.load(open(prev/'saved_world.pkl','rb'));names=d['names'];parents=d['parents'];ix={n:i for i,n in enumerate(names)}
base_rot=R.from_euler('z',90,degrees=True).as_matrix();hip=np.array([15.,9.,-11.]);action=np.array([24.,0.,-5.]);outdir=r/'Motion';outdir.mkdir(exist_ok=True)
families=list(d['profiles']);profiles={f:[] for f in families};outcache={};report={}
right_only='--right-only' in sys.argv
previous=pickle.load(open(r/'candidate_world.pkl','rb')) if right_only else {}
normal=np.array([[0,0],[.3,.2],[1.05,.65],[1.45,1.],[2.45,1.65],[3.1,2.3],[3.55,2.6],[4.75,3.55],[5.65,4.35],[6.1,4.7],[6.85,5.1],[7.3,5.4],[7.65,5.72],[8.1,6.1],[8.8,6.5]])
empty_keys=np.array([[0,0],[.35,.2],[1.1,.65],[1.5,1.],[2.7,1.7],[4.,2.65],[5.2,3.45],[5.65,3.8],[6.3,4.2],[7.05,4.82],[7.6,5.13],[8.05,5.36],[8.3,5.48],[8.7,5.82],[9.1,6.15],[9.6,6.6]])
def framing(t,empty,end):
 k=empty_keys if empty else normal;runtime=np.interp(t,k[:,1],k[:,0]);window=.72 if empty else .74
 return min(1-np.exp(-16*runtime),1-ease((t-(end-window))/window))
def turn(a,b,x):return Slerp([0,1],R.from_matrix([a,b]))([x]).as_matrix()[0]
def local(w,i):return np.linalg.inv(w[parents[i]])@w[i] if parents[i]>=0 else w[i]
digits=[i for i,n in enumerate(names) if n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky'))]
# Measured native-skinned clearance: keep the early fingertips behind the
# upright cover, then approach its contact side as the wrist finishes turning.
cover_clearance=PchipInterpolator([4.18,4.25,4.28,4.32,4.36,4.4,4.45],[0.,.5,1.5,6.5,7.5,3.5,0.])
for key in ['box_reload','box_reload_empty']:
 empty=key.endswith('empty');original_base=cache[key+'_base']['world'];times=cache[key+'_base']['times'];end=times[-1]
 path=next(p for p in d['clips'] if '/SideMagazine' not in p and p.split('.')[0].endswith('_'+('reload_empty' if empty else 'reload')));baked_base=None;right_solution=None
 for family in families:
  old=cache[key+'_'+family]['world'];w=previous[key+'_'+family]['world'].copy() if right_only else old.copy();hand=ix['hand_l'];root=ix['WPN_root']
  if family in ['canted','angled'] and not right_only:
   # The old geometric-distance gate reversed a large wrist offset in two frames.
   # Give release/regrip their own free-hand windows, ending before each contact.
   windows=[(.16,.52,True),(1.22 if empty else 2.12,1.7 if empty else 2.6,False)]
   for begin,finish,release in windows:
    ref=round((begin if release else finish)*120);rb=np.linalg.inv(original_base[ref,root])@original_base[ref,hand];rf=np.linalg.inv(old[ref,root])@old[ref,hand]
    dp=rf[:3,3]-rb[:3,3];dq=rot(rf)@rot(rb).T
    finger_delta={i:local(old[ref],i)@np.linalg.inv(local(original_base[ref],i)) for i in digits}
    for k,t in enumerate(times):
     if t<begin or t>finish:continue
     gain=(1-ease((t-begin)/(finish-begin))) if release else ease((t-begin)/(finish-begin))
     b=original_base[k];rel=np.linalg.inv(b[root])@b[hand];goal=rel.copy();goal[:3,3]+=dp*gain;goal[:3,:3]=turn(np.eye(3),dq,gain)@rel[:3,:3];w[k,hand]=b[root]@goal
     for i in digits:
      dl=mix(np.eye(4),finger_delta[i],gain);w[k,i]=w[k,parents[i]]@dl@local(b,i)
     ik=ix.get('ik_hand_l')
     if ik is not None:w[k,ik]=w[k,hand]@np.linalg.inv(old[k,hand])@old[k,ik]
  # Refit the right palm to the M249 cover, not the inherited PKM sweep.
  # Once contact starts the hand and fingers share the cover transform.  The
  # measured 3.35 cm cover-normal correction clears the native hand surface.
  cover=ix['PKM_Cover'];right=ix['hand_r'];right_digits=[i for i,n in enumerate(names) if n.endswith('_r') and n.startswith(('thumb','index','middle','ring','pinky'))]
  ref=round((4.5 if empty else 5.4)*120);held=np.linalg.inv(old[ref,cover])@old[ref,right]
  held[:3,3]+=np.array([0.,0.,.0335])
  feed_ref=round((4.18 if empty else 5.08)*120);feed_local=np.linalg.inv(old[feed_ref,root])@old[feed_ref,right]
  for k,t in enumerate(times):
   clock=t if empty else t-.9
   if not 3.5<clock<(5.06 if empty else 5.35):continue
   feed=old[k,right].copy() if clock<4.18 else old[k,root]@feed_local
   feed[:3,3]+=rot(old[k,root])@np.array([0.,-5.,6.])*ease((clock-3.5)/.3)
   goal=old[k,cover]@held
   if clock<4.45:
    gain=ease((clock-4.18)/.27);target=mix(feed,goal,gain)
    target[:3,3]+=rot(old[k,root])@np.array([-12. if empty else -14.,0.,3.])*np.sin(np.pi*gain)
    target[:3,3]+=rot(old[k,cover])@np.array([0.,0.,float(cover_clearance(np.clip(clock,4.18,4.45)))])
   elif clock<=4.82:gain=1.;target=goal
   else:
    gain=1-ease((clock-4.82)/.24);target=mix(old[k,right],goal,gain)
    target[:3,3]+=rot(old[k,root])@np.array([-9.,0.,3.])*np.sin(np.pi*gain)
   if not empty:
    optic_clear=ease((clock-4.34)/.025)*(1-ease((clock-4.395)/.025))
    target[:3,3]+=rot(old[k,root])@np.array([0.,0.,1.25])*optic_clear
    return_clear=ease((clock-4.94)/.08)*(1-ease((clock-5.2)/.15))
    target[:3,3]+=rot(old[k,root])@np.array([-6.,0.,0.])*return_clear
   w[k,right]=target
   finger_frame=feed_ref if 4.18<=clock<4.45 else k
   for i in right_digits:w[k,i]=w[k,parents[i]]@mix(local(old[finger_frame],i),local(old[ref],i),gain)
   ik=ix.get('ik_hand_r')
   if ik is not None:w[k,ik]=target@np.linalg.inv(old[k,right])@old[k,ik]
  for side in ['l','r']:
   if right_only and side=='l':continue
   b,bn=binding(side);ids=[ix[n] for n in bn];cl,up,lo,ha=[ix[n+'_'+side] for n in ['clavicle','upperarm','lowerarm','hand']]
   if side=='r' and right_solution is not None:w[:,ids]=right_solution;continue
   for k,t in enumerate(times):
    fade=ease(t/.25)*(1-ease((t-(end-.35))/.35));shift=base_rot.T@((hip-action)*framing(t,empty,end))
    # Keep the cut shoulder rim at the hidden idle shoulder; move the elbow,
    # never the contacted palm or the gun, to accommodate the safer action anchor.
    target=old[0,up,:3,3]+shift;a=old[k,up,:3,3]*(1-fade)+target*fade
    w[k,cl]=mix(old[k,cl],old[0,cl],fade);w[k,cl,:3,3]=old[k,cl,:3,3]*(1-fade)+(old[0,cl,:3,3]+shift)*fade
    olda,olde,oldh=[old[k,i,:3,3] for i in [up,lo,ha]];h=w[k,ha,:3,3];la=np.linalg.norm(olde-olda);lb=np.linalg.norm(oldh-olde);axis=unit(h-a);dist=np.linalg.norm(h-a)
    if dist>la+lb-.15:
     correction=axis*(dist-(la+lb-.15));a+=correction;w[k,cl,:3,3]+=correction;dist=la+lb-.15
    along=(la*la-lb*lb+dist*dist)/(2*dist);radius=np.sqrt(max(0.,la*la-along*along));pole=unit(olde-a-axis*((olde-a)@axis))
    # Choose a nearby elbow plane that relieves wrist swing with a fixed palm.
    preferred=unit(rot(w[k,ha])@b.R[7].T@b.F0)
    def cost(angle):
     p=R.from_rotvec(axis*angle).as_matrix()@pole;e=a+axis*along+p*radius;fore=unit(h-e);swing=np.arccos(np.clip(preferred@fore,-1,1));return max(0,swing-np.radians(42))**2+.08*angle**2
    angle=minimize_scalar(cost,bounds=(-.9,.9),method='bounded',options={'xatol':1.e-6}).x
    w[k,up,:3,3]=a;w[k,lo,:3,3]=a+axis*along+(R.from_rotvec(axis*angle).as_matrix()@pole)*radius
    old_normal=unit(np.cross(olde-olda,oldh-olde));new_normal=unit(np.cross(w[k,lo,:3,3]-a,h-w[k,lo,:3,3]))
    transport=frame(w[k,lo,:3,3]-a,new_normal)@frame(olde-olda,old_normal).T
    w[k,up,:3,:3]=transport@old[k,up,:3,:3]
   hinge.CAP=np.radians(110.);solved,info=hinge.solve(w[:,ids],b)
   for k,t in enumerate(times):
    fade=ease(t/.25)*(1-ease((t-(end-.35))/.35))
    for j in range(1,7):
     # Leave the exact idle endpoints and auxiliary-bone layout intact.
     w[k,ids[j]]=mix(old[k,ids[j]],solved[k][j],fade)
   if side=='r':right_solution=w[:,ids].copy()
  rows=encode(w)
  if family=='base':
   baked_base=rows.copy()
   with gzip.open(outdir/(key+'.json.gz'),'wt') as f:json.dump(dict(asset=path.split('.')[0],fps=120,duration=end,tracks={n:rows[:,i].tolist() for i,n in enumerate(names)}),f,separators=(',',':'))
  deltas=[]
  for i,n in enumerate(names):
   v=np.zeros((len(times),10));v[:,:3]=rows[:,i,:3]-baked_base[:,i,:3];v[:,3:7]=(R.from_quat(rows[:,i,3:7])*R.from_quat(baked_base[:,i,3:7]).inv()).as_quat();v[:,7:]=rows[:,i,7:]-baked_base[:,i,7:]
   for k in range(1,len(v)):
    if v[k-1,3:7]@v[k,3:7]<0:v[k,3:7]*=-1
   if np.max(abs(v-[0,0,0,0,0,0,1,0,0,0]))>1.e-6:deltas.append(dict(bone=n,times=times.tolist(),values=v.ravel().tolist()))
  profiles[family].append(dict(base=path.split('.')[0],duration=end,tracks=deltas));outcache[key+'_'+family]=dict(times=times,world=w)
  m=w[:,hand,:3,:3].copy();m/=np.linalg.norm(m,axis=1)[:,None,:];q=R.from_matrix(m);step=np.degrees((q[:-1].inv()*q[1:]).magnitude());report[key+'_'+family]=dict(hand_rotation_step=float(step.max()),source=float(times[step.argmax()]))
  print(key,family,report[key+'_'+family],flush=True)
for family,clips in profiles.items():
 with gzip.open(r/(family+'.json.gz'),'wt') as f:json.dump(dict(family=family,clips=clips),f,separators=(',',':'))
with (r/'candidate_world.pkl').open('wb') as f:pickle.dump(outcache,f)
(r/'authoring.json').write_text(json.dumps(report,indent=2))
