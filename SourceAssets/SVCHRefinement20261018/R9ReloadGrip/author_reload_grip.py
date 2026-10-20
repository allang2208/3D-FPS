"""Register the accepted SVD/V9 grasp onto SVCH's actual magazine shell.

Only the two reload left-arm registration tracks are authored. Native fingers,
right arm, magazine/gun motion and source clocks remain in the saved profile.
"""
import copy,gzip,json,sys
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation as R,Slerp

O=Path(__file__).parent;I=O/'Inputs'
sys.path.insert(0,str(O.parents[1]/'HK416ReloadGrip20261001'))
from author_drum import Surface,matrices,unit
load=lambda n:json.load(gzip.open(I/(n+'.json.gz'),'rt',encoding='utf-8'))
data={n:load(n) for n in ('svch','svd','arms')};motion=load('motion')
N=motion['names'];NI={n:i for i,n in enumerate(N)};PI=[NI.get(p,-1) for p in motion['parents']]
MAG=NI['WPN_SOCKET_Magazine'];ROOT=NI['WPN_root'];HAND=NI['hand_l']
profile=json.loads((I/'profile_before.json').read_text());output=copy.deepcopy(profile)
rest={k:matrices(v['reference']) for k,v in data.items()}
left_chain=[n for n in N if n.endswith('_l') and n.startswith(('clavicle','upperarm','lowerarm','hand_'))]

def comp(local):
 p=local.copy()
 for i,parent in enumerate(PI):
  if parent>=0:p[i]=p[parent]@p[i]
 return p
def rigid(m):
 out=m.copy();out[:3,:3]/=np.linalg.norm(out[:3,:3],axis=0);return out
def points(m,p):return np.asarray(p)@m[:3,:3].T+m[:3,3]
def mix(a,b,w):
 out=a.copy();out[:3,3]=(1-w)*a[:3,3]+w*b[:3,3]
 scale=np.linalg.norm(a[:3,:3],axis=0)
 out[:3,:3]=Slerp([0,1],R.from_matrix([rigid(a)[:3,:3],rigid(b)[:3,:3]]))([w]).as_matrix()[0]*scale
 return out
def ease(a,b,t):
 x=np.clip((t-a)/(b-a),0,1);return x*x*x*(10-15*x+6*x*x)
def old_pose(base,clip,t):
 row=base.copy()
 for track in clip['tracks']:
  i=NI[track['bone']];ts=np.asarray(track['times']);vs=np.asarray(track['values']).reshape(-1,10)
  if len(ts)==1:v=vs[0]
  else:
   j=int(np.clip(np.searchsorted(ts,t)-1,0,len(ts)-2));w=np.clip((t-ts[j])/(ts[j+1]-ts[j]),0,1)
   v=vs[j]*(1-w)+vs[j+1]*w;v[3:7]=Slerp([0,1],R.from_quat(vs[j:j+2,3:7]))([w]).as_quat()[0]
  row[i,:3]+=v[:3];row[i,3:7]=(R.from_quat(v[3:7])*R.from_quat(base[i,3:7])).as_quat();row[i,7:]+=v[7:]
 return row
def geom(key,material):
 d=data[key];v=np.asarray(d['positions']);tri=np.asarray(d['triangles']);ids=np.asarray(d['material_ids'])
 selected=[i for i,n in enumerate(d['materials']) if material(n)]
 tri=tri[np.isin(ids,selected)];unique=np.unique(tri);remap=np.zeros(len(v),int);remap[unique]=np.arange(len(unique))
 return v[unique],remap[tri]
def surface(v,t):
 a,b,c=(v[t]-v.mean(0)).transpose(1,0,2)
 volume=np.einsum('ij,ij->i',a,np.cross(b,c)).sum()/6
 return Surface(v,t if volume>=0 else t[:,::-1])

mag={}
for k in ('svd','svch'):
 v,t=geom(k,lambda n:'Magazine' in n)
 mag[k]=(points(np.linalg.inv(rigid(rest[k][MAG])),v),t)
surfaces={k:surface(*v) for k,v in mag.items()}
arms=data['arms'];AV=np.asarray(arms['positions']);AW=np.zeros((len(AV),len(N)))
for i,row in enumerate(arms['weights']):
 for b,w in row:AW[i,NI[arms['weight_bones'][b]]]=w
AI=np.linalg.inv(rest['arms']);DOM=AW.argmax(1)
HANDIDS=np.flatnonzero(np.array([N[b].endswith('_l') and N[b].startswith(('hand_','thumb','index','middle','ring','pinky')) for b in DOM]))
def skin(pose,ids):
 result=np.zeros((len(ids),3))
 for b in np.flatnonzero(AW[ids].max(0)>0):result+=points(pose[b]@AI[b],AV[ids])*AW[ids,b,None]
 return result

class Shell:
 def __init__(self,pts,up):
  self.pts=pts;_,_,v=np.linalg.svd(pts-pts.mean(0),full_matrices=False);axis=v[0]
  heights=pts@axis;spine=[]
  for a,b in zip(np.linspace(heights.min(),heights.max(),29)[:-1],np.linspace(heights.min(),heights.max(),29)[1:]):
   chunk=pts[(heights>=a)&(heights<b)]
   if len(chunk)>4:spine.append((chunk.min(0)+chunk.max(0))*.5)
  s=np.asarray(spine);_,_,v=np.linalg.svd(s-s.mean(0),full_matrices=False);self.axis=v[0]
  if self.axis@up<0:self.axis=-self.axis
  self.low=float((pts@self.axis).min());self.high=float((pts@self.axis).max());self.length=self.high-self.low
 def frame(self,height,palm):
  level=self.low+height;heights=self.pts@self.axis
  part=self.pts[np.abs(heights-level)<.75]
  if len(part)<20:part=self.pts[np.argsort(abs(heights-level))[:120]]
  c=part.mean(0);rel=part-c-np.outer((part-c)@self.axis,self.axis)
  _,_,v=np.linalg.svd(rel,full_matrices=False);thin=unit(np.cross(self.axis,v[0]))
  if thin@(palm-c)<0:thin=-thin
  wide=unit(np.cross(thin,self.axis));thin=unit(np.cross(self.axis,wide))
  c+=self.axis*(level-c@self.axis)
  c+=wide*.5*(((part-c)@wide).min()+((part-c)@wide).max())
  c+=thin*.5*(((part-c)@thin).min()+((part-c)@thin).max())
  f=np.eye(4);f[:3,:3]=np.column_stack((self.axis,wide,thin));f[:3,3]=c
  return f,np.array([np.ptp(part@wide),np.ptp(part@thin)])

def swing(a,b):
 a,b=unit(a),unit(b);cross=np.cross(a,b);dot=np.clip(a@b,-1,1)
 return np.eye(3) if np.linalg.norm(cross)<1e-10 else R.from_rotvec(unit(cross)*np.arctan2(np.linalg.norm(cross),dot)).as_matrix()
def aimed(old,oldend,start,end):
 p=old.copy();p[:3,:3]=swing(oldend-old[:3,3],end-start)@old[:3,:3];p[:3,3]=start;return p
def solve_arm(old,hand):
 p=old.copy();ci,ui,li,hi=[NI[x+'_l'] for x in ('clavicle','upperarm','lowerarm','hand')]
 shoulder,elbow,wrist=[old[j,:3,3].copy() for j in (ui,li,hi)];target=hand[:3,3]
 l1,l2=np.linalg.norm(elbow-shoulder),np.linalg.norm(wrist-elbow)
 if np.linalg.norm(target-shoulder)>l1+l2-.4:
  c=old[ci,:3,3];radius=np.linalg.norm(shoulder-c);d=np.linalg.norm(target-c);axis=unit(target-c)
  side=unit(shoulder-c-axis*((shoulder-c)@axis));cos=np.clip((radius*radius+d*d-(l1+l2-.4)**2)/(2*radius*d),-1,1)
  shoulder=c+axis*radius*cos+side*radius*np.sqrt(max(0,1-cos*cos));p[ci]=aimed(old[ci],old[ui,:3,3],c,shoulder)
 axis=unit(target-shoulder);d=np.linalg.norm(target-shoulder);pole=unit(elbow-shoulder-axis*((elbow-shoulder)@axis))
 along=(l1*l1-l2*l2+d*d)/(2*max(d,1e-9));e=shoulder+axis*along+pole*np.sqrt(max(0,l1*l1-along*along))
 du=aimed(old[ui],elbow,shoulder,e)@np.linalg.inv(old[ui]);dl=aimed(old[li],wrist,e,target)@np.linalg.inv(old[li])
 for n in left_chain:
  i=NI[n]
  if n.startswith('upperarm'):p[i]=du@old[i]
  elif n.startswith('lowerarm'):p[i]=dl@old[i]
 p[hi]=hand
 # Preserve the native wrist shape while distributing only the extra axial
 # rotation from registration over the V9 near/mid forearm helper bones.
 fore_old=R.from_matrix(rigid(old[li])[:3,:3]);fore_new=R.from_matrix(rigid(p[li])[:3,:3])
 relative_old=fore_old.inv()*R.from_matrix(rigid(old[hi])[:3,:3])
 relative_new=fore_new.inv()*R.from_matrix(rigid(hand)[:3,:3])
 delta=(relative_new*relative_old.inv()).as_quat()
 if delta[3]<0:delta=-delta
 fore_axis=fore_old.inv().apply(unit(wrist-elbow));roll=2*np.arctan2(delta[:3]@fore_axis,delta[3])
 for name,share in (('lowerarm_twist_01_l',1.),('lowerarm_twist_02_l',.5)):
  j=NI[name];change=fore_new*R.from_rotvec(fore_axis*roll*share)*fore_new.inv()
  p[j,:3,:3]=change.as_matrix()@p[j,:3,:3]
 return p

report={'method':'Magazine-shell front-half registration with bounded rigid fitting; original V9 fingers and all non-reload tracks preserved',
        'runtime_tested':False,'clips':{}}
body_v,body_t=geom('svch',lambda n:n in ('SVCH_Body','SVCH_Polymer','SVCH_Rubber','SVCH_BarrelSteel'))
shared_grasp=None;shared_candidates=None
for role in ('reload','reload_empty'):
 clip=motion['clips'][role];entry=next(c for c in output['clips'] if c['base']==clip['path'])
 before=next(c for c in profile['clips'] if c['base']==clip['path'])
 base=np.asarray(clip['frames']);poses=[comp(matrices(frame)) for frame in base]
 k=220;pose=poses[k];pm=rigid(pose[MAG]);mag_inv=np.linalg.inv(pm)
 hmag=points(mag_inv,skin(pose,HANDIDS));palm=points(mag_inv,pose[HAND:HAND+1,:3,3])[0]
 knuckle=points(mag_inv,np.mean([pose[NI[d+'_01_l'],:3,3] for d in ('index','middle','ring','pinky')],axis=0)[None])[0]
 root_positions=[(np.linalg.inv(rigid(poses[f][ROOT]))@rigid(poses[f][MAG]))[:3,3] for f in (170,240)]
 up=mag_inv[:3,:3]@rigid(pose[ROOT])[:3,:3]@(root_positions[1]-root_positions[0])
 source=Shell(mag['svd'][0],up);target=Shell(mag['svch'][0],up)
 source_height=float(knuckle@source.axis-source.low);fs,size_s=source.frame(source_height,palm)
 # SVD's accepted hand wraps the front half. Preserve distances to that edge
 # and the palm-side face when the target magazine has a different width.
 edge=1 if (knuckle-fs[:3,3])@fs[:3,1]>=0 else -1
 fs[:3,3]+=fs[:3,1]*edge*size_s[0]*.5+fs[:3,2]*size_s[1]*.5
 old_local=old_pose(base[k],before,clip['times'][k]);old_world=comp(matrices(old_local))
 pads=[]
 for n in N:
  if not n.endswith('_l') or not n.startswith(('thumb','index','middle','ring','pinky')):continue
  ids=np.flatnonzero(DOM[HANDIDS]==NI[n])
  if len(ids):
   _,_,dist=surfaces['svd'].nearest(hmag[ids]);pads.extend(ids[np.argsort(dist)[:min(12,len(ids))]].tolist())
 pads=np.unique(pads);contact=hmag[pads];cp,cn,cd=surfaces['svd'].nearest(contact)
 goals=np.einsum('ij,ij->i',contact-cp,cn)
 clearance=hmag[::max(1,len(hmag)//180)]
 bodies=[]
 for context in ('reload','reload_empty'):
  for f in (49,220,240,244):
   bp=comp(matrices(motion['clips'][context]['frames'][f]))
   m=np.linalg.inv(rigid(bp[MAG]))@bp[ROOT]@np.linalg.inv(rest['svch'][ROOT])
   verts=points(m,body_v);bodies.append(surface(verts,body_t))
 candidates=[]
 heights={'floorplate':source_height,'feed':target.length-(source.length-source_height),'relative':target.length*source_height/source.length}
 for convention,height in (heights.items() if shared_grasp is None else []):
  height=float(np.clip(height,.8,target.length-.8));ft,size_t=target.frame(height,palm)
  ft[:3,3]+=ft[:3,1]*edge*size_t[0]*.5+ft[:3,2]*size_t[1]*.5
  nominal=ft@np.linalg.inv(fs)
  def transform(x):
   delta=np.eye(4);delta[:3,:3]=R.from_rotvec(x[3:]).as_matrix();delta[:3,3]=x[:3]
   return ft@delta@np.linalg.inv(ft)@nominal
  def residual(x):
   m=transform(x);moved=points(m,contact);q,n,d=surfaces['svch'].nearest(moved)
   signed=np.einsum('ij,ij->i',moved-q,n)
   fit=signed-goals;close=points(m,clearance);body_pen=[]
   for body in bodies:
    q,n,d=body.nearest(close);s=np.einsum('ij,ij->i',close-q,n)
    body_pen.extend((np.where(d<2.5,np.minimum(s+.12,0),0)*2.).tolist())
   return np.r_[fit,np.minimum(signed+.10,0)*2.,body_pen,x[:3]*.12,x[3:]*2.]
  objective=lambda x:float(np.mean(residual(x)**2))
  # Closest-triangle switches make finite-difference Jacobians unreliable at
  # the shell's bevels; bounded Powell keeps the actual surface objective.
  opt=minimize(objective,np.zeros(6),method='Powell',bounds=[(-1.,1.)]*3+[(-np.deg2rad(8),np.deg2rad(8))]*3,
      options={'maxiter':18,'maxfev':750,'xtol':.0005,'ftol':.0001})
  score=objective(opt.x);mapping=transform(opt.x)
  candidates.append((score,mapping,{'height_convention':convention,'height_from_floor_cm':height,
      'translation_shell_cm':opt.x[:3].tolist(),'rotation_shell_deg':np.rad2deg(opt.x[3:]).tolist(),
      'target_cross_section_cm':size_t.tolist(),'fit_objective':score}))
 if shared_grasp is None:
  chosen=min(candidates,key=lambda v:v[0]);shared_grasp=chosen;shared_candidates=candidates
 else:chosen=shared_grasp;candidates=shared_candidates
 mapping=chosen[1]
 _,_,source_dist=surfaces['svd'].nearest(hmag)
 q0,_,d0=surfaces['svch'].nearest(hmag)
 q1,_,d1=surfaces['svch'].nearest(points(mapping,hmag))
 contact_metrics={}
 for digit in ('thumb','index','middle','ring','pinky'):
  ix=np.array([j for j,v in enumerate(HANDIDS) if N[DOM[v]].startswith(digit)])
  contact_metrics[digit]={'accepted_source_median_gap_mm':float(np.median(source_dist[ix])*10),
      'before_median_gap_mm':float(np.median(d0[ix])*10),'authored_median_gap_mm':float(np.median(d1[ix])*10)}
 tracks={n:[] for n in left_chain};active=0;max_hand_shift=0.;max_fk_wrist_error=0.
 for i,t in enumerate(clip['times']):
  old=old_pose(base[i],before,t);p=comp(matrices(old));w=float(ease(18,49,t*120)*(1-ease(244,302,t*120)))
  updated=p
  if w>1e-9:
   active+=1;anchor=rigid(poses[i][MAG]);desired=anchor@mapping@np.linalg.inv(anchor)@poses[i][HAND]
   hand=mix(p[HAND],desired,w);max_hand_shift=max(max_hand_shift,float(np.linalg.norm(hand[:3,3]-p[HAND,:3,3])))
   updated=solve_arm(p,hand)
  authored_local=old.copy()
  for n in left_chain:
   j=NI[n]
   if w<=1e-9:
    original=next((v for v in before['tracks'] if v['bone']==n),None)
    # old local pose already contains the exact current profile sample.
    loc=matrices(old)[j]
   else:loc=np.linalg.solve(updated[PI[j]],updated[j])
   rot=R.from_matrix(rigid(loc)[:3,:3])*R.from_quat(base[i,j,3:7]).inv()
   # Rotation-only arm registration preserves original local offsets/scale.
   values=[*(old[j,:3]-base[i,j,:3]),*rot.as_quat(),*(old[j,7:]-base[i,j,7:])]
   if tracks[n] and np.dot(tracks[n][-1][3:7],values[3:7])<0:values[3:7]=[-v for v in values[3:7]]
   tracks[n].append(values)
   authored_local[j,3:7]=(rot*R.from_quat(base[i,j,3:7])).as_quat()
  if w>1e-9:
   authored_world=comp(matrices(authored_local))
   max_fk_wrist_error=max(max_fk_wrist_error,float(np.linalg.norm(authored_world[HAND,:3,3]-hand[:3,3])))
 entry['tracks']=[v for v in entry['tracks'] if v['bone'] not in left_chain]
 for n,values in tracks.items():entry['tracks'].append({'bone':n,'times':clip['times'],'values':np.round(values,10).ravel().tolist()})
 report['clips'][role]={'source_length_cm':source.length,'target_length_cm':target.length,'source_grip_height_cm':source_height,
    'source_cross_section_cm':size_s.tolist(),'candidates':[c[2] for c in candidates],'selected':chosen[2],
    'magazine_local_registration':mapping.tolist(),'max_wrist_registration_cm':max_hand_shift,'active_samples':active,
    'source_frames':[18,49,244,302],'modified_tracks':left_chain,'finger_tracks_modified':False,
    'authoring_surface_metrics':contact_metrics,'max_fk_wrist_error_cm':max_fk_wrist_error,
    'extra_wrist_twist_distribution':'V9 near 100%, mid 50%; helper bones only','same_grasp_for_both_reloads':True}
 print('SVCH_RELOAD_AUTHORED',role,json.dumps(report['clips'][role]),flush=True)
(O/'profile_reload_grip.json').write_text(json.dumps(output,separators=(',',':')))
(O/'authoring_receipt.json').write_text(json.dumps(report,indent=2))
print('SVCH_RELOAD_AUTHORING_COMPLETE',flush=True)
