"""Author gun-aware support-arm clearance in the existing six inspect layers.

The hand contact, fingers, right arm, gun and action clock are retained. Elbow
swivel is solved on the exact two-bone circle. A bounded shoulder translation
is available when the original nearly straight chain leaves no exterior route.
"""
import json,sys,copy,math
from pathlib import Path
import numpy as np
import trimesh
from scipy.optimize import differential_evolution, minimize
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation as Rot,Slerp
from scipy.ndimage import gaussian_filter1d,maximum_filter1d
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KInspectClearance20261018'
sys.path.insert(0,str(P/'Tools/Saiga12KInspect'))
from pose_math import matrix,rotation,pack,world,apply
code=(P/'Tools/Saiga12KInspect/author_profiles.py').read_text();exec(code[code.index('def sparse_track'):code.index('\ntimes=np.asarray')])
d=json.loads((O/'Inputs/runtime-source.json').read_text());names=[b['name'] for b in d['bones']];parents={b['name']:names[b['parent']] if b['parent']>=0 else None for b in d['bones']}
inverse_rest={n:np.linalg.inv(matrix(d['reference'][n])) for n in names}
upper=('upperarm_l','upperarm_twist_01_l','upperarm_twist_02_l');lower=('lowerarm_l','lowerarm_twist_02_l','lowerarm_twist_01_l');chain=('clavicle_l',)+upper+lower+('hand_l',)
groups=(set(upper),set(lower),{'clavicle_l'});armids={i for i,n in enumerate(names) if n in set(upper+lower)}
skin=[v for v in d['skin']['vertices'].values() if sum(w for b,w in v['w'] if b in armids)>.2][::7]
points=np.array([np.r_[v['p'],1.] for v in skin]);indices=np.zeros((len(skin),8),dtype=int);weights=np.zeros((len(skin),8))
for i,v in enumerate(skin):
 for j,(b,w) in enumerate(v['w']):indices[i,j]=b;weights[i,j]=w
group_weights=[weights*np.isin(indices,[i for i,n in enumerate(names) if n in g]) for g in groups];group_weights.append(weights-sum(group_weights))
gun=json.loads((P/'SourceAssets/Saiga12KClosure20261018/Authoring/gun.json').read_text());gp=np.array(gun['positions']);gt=np.array(gun['triangles']);gpart=np.array(gun['parts']);boxes=[]
for part in ('Handguard','ReceiverCover'):
 v=gp[np.unique(gt[gpart==part])];boxes.append(((v.min(0)+v.max(0))/2,(v.max(0)-v.min(0))/2))
# Use disconnected receiver solids: its complete bounds incorrectly fill the
# empty space below the gas tube and around the handguard.
body=trimesh.Trimesh(vertices=gp,faces=gt[gpart=='Body'],process=True)
for component in body.split(only_watertight=False):
 if len(component.faces)<300:continue
 lo,hi=component.bounds
 if np.min(hi-lo)<.05:continue
 boxes.append(((lo+hi)/2,(hi-lo)/2))

mag_hull=ConvexHull(gp[np.unique(gt[gpart=='Magazine'])]).equations
# Merge coplanar facets before using this conservative solid in the fitter.
mag_hull=np.unique(np.round(mag_hull,6),axis=0)
def sdf(p):
 out=np.full(p.shape[:-1],1e3)
 for center,half in boxes:
  q=np.abs(p-center)-half;dist=np.linalg.norm(np.maximum(q,0),axis=-1)+np.minimum(np.max(q,axis=-1),0);out=np.minimum(out,dist)
 out=np.minimum(out,np.max(p@mag_hull[:,:3].T+mag_hull[:,3],axis=-1))
 return out
def unit(x):return x/max(np.linalg.norm(x),1e-12)
def swing(a,b):
 a=unit(a);b=unit(b);axis=np.cross(a,b);mag=np.linalg.norm(axis)
 if mag<1e-10:return np.eye(3)
 return Rot.from_rotvec(axis/mag*math.atan2(mag,np.clip(a@b,-1,1))).as_matrix()
def pivot(r,a,b):
 m=np.eye(4);m[:3,:3]=r;m[:3,3]=b-r@a;return m
def transforms(w,theta,shift,shorten=0.):
 A,E,H=[w[n][:3,3] for n in ('upperarm_l','lowerarm_l','hand_l')]
 if abs(theta)<1e-10 and abs(shift)<1e-10 and abs(shorten)<1e-10:return (np.eye(4),np.eye(4),np.eye(4))
 u=E-A;f=H-E;L1=np.linalg.norm(u);L2=np.linalg.norm(f);direction=rotation(w['WPN_root'])[:,0];q=A+unit(H-A)*shorten-H;projection=q@direction
 maximum=-projection+math.sqrt(max(0.,projection*projection+(L1+L2-.00001)**2-q@q));shift=float(np.clip(shift,0,max(0.,maximum)))
 newA=A+direction*shift+unit(H-A)*shorten;axis=unit(H-newA);distance=np.linalg.norm(H-newA)
 along=(L1*L1-L2*L2+distance*distance)/(2*distance);radius=math.sqrt(max(0.,L1*L1-along*along));v=E-newA;pole=unit(v-axis*(v@axis));newE=newA+axis*along+Rot.from_rotvec(axis*np.deg2rad(theta)).apply(pole)*radius
 return (pivot(swing(u,newE-newA),A,newA),pivot(swing(f,H-newE),E,newE),pivot(np.eye(3),A,newA))
def cache(frame,clip):
 original={n:matrix(v) for n,v in frame['local'].items()};local=apply(original,clip,frame['time']);w=world(local,parents)
 matrices=np.array([w[n]@inverse_rest[n] for n in names]);deform=np.einsum('nkij,nj->nki',matrices[indices],points)
 terms=[np.einsum('nki,nk->ni',deform,gw) for gw in group_weights]
 return original,local,w,terms,np.linalg.inv(w['WPN_root'])
def moved_points(item,tr):
 _,_,_,terms,inv=item
 return ((terms[0]@tr[0].T+terms[1]@tr[1].T+terms[2]@tr[2].T+terms[3])@inv.T)[:,:3]*100
times=np.array([f['time'] for f in d['frames']]);sample_ids=sorted(set(range(0,len(times),6))|{len(times)-1});sample_times=times[sample_ids]
report={'complete':False,'source_clip':d['clip'],'source_profile_root':'/Game/Weapons/Saiga12K/Drum20261018/Profiles','families':{},'runtime_tested':False,'method':'Fixed palm and fingers; elbow swivel and modest arm-root adjustment to route the support forearm outside the handguard. Native segment lengths and shared clip timing retained.'}
# These families are already using distinct accepted hand contacts. Keep the
# unaffected inspect layers, including bare-hand and drum-only, unchanged.
for family in ('base','drum','angled'):
 profile=copy.deepcopy(d['profiles'][family]);profile['family']=family
 (O/'Profiles'/('DA_'+family+'.json')).write_text(json.dumps(profile),encoding='utf8')
 report['families'][family]={'all_clips_retained':True}
for family in ('vertical','prism','canted'):
 profile=copy.deepcopy(d['profiles'][family]);clip=next(c for c in profile['clips'] if c['base']==d['clip']);samples=[cache(d['frames'][i],clip) for i in sample_ids];params=[];previous=np.zeros(3)
 for i,item in enumerate(samples):
  t=sample_times[i]
  def cost(v):
   tr=transforms(item[2],*v);pen=np.maximum(.65-sdf(moved_points(item,tr)),0.)
   # Clearance is the primary authoring constraint. Prefer a small anatomical
   # adjustment; the shoulder follows the arm, never scales the bone chain.
   return 10000*float(np.max(pen)**2)+300*float(np.mean(pen**2))+.0003*v[0]**2+.1*np.linalg.norm(tr[2][:3,3])**2
  if t<.18 or t>d['duration']-.18 or cost(np.zeros(3))<1e-8:
   value=np.zeros(3)
  else:
   result=differential_evolution(cost,[(-75.,75.),(0.,7.),(0.,8.)],popsize=7,maxiter=32,tol=.004,seed=100+i,x0=previous)
   value=result.x
  params.append(value);previous=value
  if i%10==0:print('CLEARANCE_AUTHOR',family,i,len(samples),flush=True)
 params=np.asarray(params)
 # Extend shoulder support into both approach and return; smoothing may reduce
 # a tight constraint, so the solve uses a 6.5 mm authoring envelope.
 params[:,1:]=gaussian_filter1d(maximum_filter1d(params[:,1:],size=3,axis=0,mode='nearest'),.7,axis=0)
 params[:,0]=gaussian_filter1d(params[:,0],.75)
 dense=np.column_stack([np.interp(times,sample_times,params[:,j]) for j in range(3)])
 fade=np.minimum(np.clip((times-.1)/.3,0,1),np.clip((d['duration']-.1-times)/.3,0,1));fade=fade*fade*(3-2*fade);dense*=fade[:,None]
 keys={n:[] for n in set([t['bone'] for t in clip['tracks']])|set(chain)};shoulder=[];clearance=[]
 for i,frame in enumerate(d['frames']):
  original,local,w,terms,inv=cache(frame,clip);tr=transforms(w,*dense[i]);shoulder.append(float(np.linalg.norm(tr[2][:3,3])));clearance.append(float(sdf(moved_points((original,local,w,terms,inv),tr)).min()))
  desired={n:tr[0]@w[n] for n in upper};desired.update({n:tr[1]@w[n] for n in lower});desired['clavicle_l']=tr[2]@w['clavicle_l'];desired['hand_l']=w['hand_l'].copy();final={}
  for n in names:
   p=parents[n]
   if n in desired:final[n]=desired[n];local[n]=np.linalg.inv(final[p])@final[n] if p else final[n]
   else:final[n]=final[p]@local[n] if p else local[n]
  for n in keys:
   a,b=pack(original[n]),pack(local[n]);dq=(Rot.from_quat(b[3:7])*Rot.from_quat(a[3:7]).inv()).as_quat();value=np.r_[b[:3]-a[:3],dq,np.zeros(3)]
   if not np.isfinite(value).all():raise RuntimeError('Invalid arm pose '+family+' '+n)
   keys[n].append(value)
 tracks=[t for n in sorted(keys) if (t:=sparse_track(n,keys[n],times)) is not None]
 newclip=dict(base=d['clip'],duration=d['duration'],retained=None,tracks=tracks);profile['clips']=[newclip if c['base']==d['clip'] else c for c in profile['clips']];profile['family']=family
 (O/'Profiles'/('DA_'+family+'.json')).write_text(json.dumps(profile),encoding='utf8')
 report['families'][family]={'tracks':len(tracks),'parameters':dense.tolist(),'shoulder_shift_cm':shoulder,'authoring_envelope_clearance_cm':clearance,'times':times.tolist(),'other_clips_retained':len(profile['clips'])-1,'palm_and_fingers_preserved':True};print('SAIGA_INSPECT_CLEARANCE_AUTHORED',family,'shoulder',max(shoulder),'envelope',min(clearance),flush=True)
report['complete']=True;(O/'Receipts/authoring.json').write_text(json.dumps(report,indent=2),encoding='utf8')

(O/'Receipts/production-ready.json').write_text(json.dumps({'authoring_complete':True,'runtime_tested':False,'changed_inspect_families':['vertical','prism','canted'],'other_clips':'retained'}),encoding='utf8')
