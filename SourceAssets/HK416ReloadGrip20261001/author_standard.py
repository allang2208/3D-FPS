"""Register accepted M4 hand shapes on HK416's actual upper magazine shell.

Ordinary and extended HK magazines retain the same feed/grasp region. The
relation is measured from the feed end, with a bounded rigid skin contact fit.
Original native arm twist, mechanical tracks and reload clocks are retained.
"""
import gzip,json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as R,Slerp
from author_drum import Surface,HandSkin,matrices,unit
O=Path(__file__).parent;I=O/'Inputs'
DIGITS=('thumb','index','middle','ring','pinky')
HAND=['hand_l']+[d+'_'+j+'_l' for d in DIGITS for j in ('metacarpal','01','02','03') if not (d=='thumb' and j=='metacarpal')]
def smooth(a,b,f):
 t=np.clip((f-a)/(b-a),0.,1.);return t*t*(3.-2.*t)
def shell_frame(points,up,palm,feed_depth=None,knuckle=None):
 center=points.mean(axis=0);_,_,V=np.linalg.svd(points-center,full_matrices=False);long=V[0]
 if np.dot(long,up)<0:long=-long
 heights=points@long;lo,hi=heights.min(),heights.max()
 # Use the cross-section spine rather than relief detail density.
 bins=np.linspace(lo,hi,25);spine=[]
 for a,b in zip(bins[:-1],bins[1:]):
  part=points[(heights>=a)&(heights<b)]
  if len(part)>5:spine.append((part.min(axis=0)+part.max(axis=0))*.5)
 sc=np.array(spine);_,_,V=np.linalg.svd(sc-sc.mean(axis=0),full_matrices=False);long=V[0]
 if np.dot(long,up)<0:long=-long
 heights=points@long;hi=heights.max();lo=heights.min()
 if feed_depth is None:feed_depth=hi-np.dot(knuckle,long)
 level=hi-feed_depth;part=points[np.abs(heights-level)<1.0]
 if len(part)<20:part=points[np.argsort(np.abs(heights-level))[:150]]
 c=part.mean(axis=0);rel=part-c-np.outer((part-c)@long,long)
 _,_,V=np.linalg.svd(rel,full_matrices=False);wide=V[0];thin=np.cross(long,wide);thin=unit(thin)
 if np.dot(thin,palm-c)<0:thin=-thin
 wide=unit(np.cross(thin,long));thin=unit(np.cross(long,wide))
 # A bounding cross-section centre prevents stamped ridges biasing the anchor.
 c+=wide*(.5*((part-c)@wide).max()+.5*((part-c)@wide).min())
 c+=thin*(.5*((part-c)@thin).max()+.5*((part-c)@thin).min())
 c+=long*(level-np.dot(c,long))
 F=np.eye(4);F[:3,:3]=np.column_stack((long,wide,thin));F[:3,3]=c
 return F,float(feed_depth),{'feed_depth_cm':float(feed_depth),'shell_length_cm':float(hi-lo),'grip_cross_section_cm':[float(np.ptp(part@wide)),float(np.ptp(part@thin))]}
def mix(a,b,w):
 if w<=0:return a.copy()
 if w>=1:return b.copy()
 q=Slerp([0,1],R.from_matrix(np.array([a[:3,:3],b[:3,:3]])))([w]).as_matrix()[0]
 out=np.eye(4);out[:3,:3]=q;out[:3,3]=a[:3,3]*(1-w)+b[:3,3]*w;return out
def aimed(old,oldend,newpos,newend):
 a=unit(oldend-old[:3,3]);b=unit(newend-newpos);v=np.cross(a,b);dot=np.clip(a@b,-1.,1.)
 rot=R.from_rotvec(unit(v)*np.arctan2(np.linalg.norm(v),dot)).as_matrix() if np.linalg.norm(v)>1e-10 else np.eye(3)
 out=old.copy();out[:3,:3]=rot@old[:3,:3];out[:3,3]=newpos;return out
def solve_arm(old,hand,names,ni):
 p=old.copy();ui=ni['upperarm_l'];li=ni['lowerarm_l'];hi=ni['hand_l'];ci=ni['clavicle_l']
 shoulder=old[ui,:3,3].copy();elbow=old[li,:3,3].copy();wrist=old[hi,:3,3].copy();target=hand[:3,3]
 l1=np.linalg.norm(elbow-shoulder);l2=np.linalg.norm(wrist-elbow)
 if np.linalg.norm(target-shoulder)>l1+l2-.4:
  c=old[ci,:3,3];radius=np.linalg.norm(shoulder-c);dist=np.linalg.norm(target-c);axis=unit(target-c)
  side=unit(shoulder-c-axis*np.dot(shoulder-c,axis));cos=np.clip((radius**2+dist**2-(l1+l2-.4)**2)/(2*radius*dist),-1,1)
  shoulder=c+axis*radius*cos+side*radius*np.sqrt(max(0,1-cos*cos));p[ci]=aimed(old[ci],old[ui,:3,3],c,shoulder)
 axis=unit(target-shoulder);dist=min(np.linalg.norm(target-shoulder),l1+l2-1e-5)
 pole=unit(elbow-shoulder-axis*np.dot(elbow-shoulder,axis));along=(l1*l1-l2*l2+dist*dist)/(2*dist)
 e=shoulder+axis*along+pole*np.sqrt(max(0.,l1*l1-along*along))
 du=aimed(old[ui],elbow,shoulder,e)@np.linalg.inv(old[ui]);dl=aimed(old[li],wrist,e,target)@np.linalg.inv(old[li])
 for n in names:
  j=ni[n]
  if n.endswith('_l') and n.startswith('upperarm'):p[j]=du@old[j]
  elif n.endswith('_l') and n.startswith('lowerarm'):p[j]=dl@old[j]
 p[hi]=hand;return p
def packed(m,original):
 q=R.from_matrix(m[:3,:3]/np.linalg.norm(m[:3,:3],axis=0)).as_quat()
 return [*m[:3,3],*q,*original[7:10]]

def main():
 bind=json.loads((I/'bind.json').read_text());index=json.loads((O/'inputs.json').read_text());donors=json.loads((O/'donor.json').read_text())
 names=bind['names'];ni={n:i for i,n in enumerate(names)};parents=np.array(bind['parents']);rest=matrices(bind['rest'])
 native=np.load(I/'HK416.npz');skin=HandSkin(native,names,rest);factory=np.load(I/'factory.npz');surface=Surface(factory['pos'],factory['tris'])
 dominant=skin.ids[np.arange(len(skin.pos)),skin.weights.argmax(axis=1)]
 body_ids={ni[n] for n in names if n.startswith('WPN_') and n!='WPN_SOCKET_Magazine'}
 is_body=np.isin(dominant,list(body_ids));body_tris=native['tris'][is_body[native['tris']].all(axis=1)]
 digit_groups={}
 for d in DIGITS:
  ids=np.concatenate([skin.groups.get(d+'_'+j+'_l',np.array([],int)) for j in ('01','02','03')])
  # HandSkin intentionally excludes thumb groups for the drum author.
  if d=='thumb':
   dominant=skin.ids[np.arange(len(skin.pos)),skin.weights.argmax(axis=1)]
   ids=np.flatnonzero(np.isin(dominant,[ni['thumb_'+j+'_l'] for j in ('01','02','03')]))
  digit_groups[d]=ids
 report={'method':'Accepted M4/AKM wrap; feed-relative shell registration; bounded native skin fit; original whole-arm twist retained','grips':{},'clips':{}}
 targets={}
 # Both new-mag clips share the accepted stable hand pose; old grips retain the
 # original toss pose instead of replacing it with the insertion wrist angle.
 for donor_key in ('reload','reload_empty','old_reload','old_reload_empty'):
  s=donors[donor_key];dm=np.array(s['mag_deform']);im=np.linalg.inv(dm);dh={n:np.array(s['deform'][n])@rest[ni[n]] for n in HAND}
  handrest={n:im@v for n,v in dh.items()};knuckle=np.mean([handrest[d+'_01_l'][:3,3] for d in DIGITS[1:]],axis=0)
  fm,depth,source_info=shell_frame(np.array(s['shell']),np.array(s['up']),handrest['hand_l'][:3,3],knuckle=knuckle)
  # Source palm direction selects the same side of the HK shell, even though the
  # source and target shell origins and lengths differ.
  hint=factory['pos'].mean(axis=0)+fm[:3,2]*15.
  fh,_,target_info=shell_frame(factory['pos'],rest[ni['WPN_root'],:3,2],hint,feed_depth=depth)
  nominal={n:fh@np.linalg.inv(fm)@v for n,v in handrest.items()}
  pose=rest.copy()
  for n,v in nominal.items():pose[ni[n]]=v
  # Clamp the fit to 8 mm / 8 degrees in shell coordinates. Digit pads use the
  # nearest side of their visible skin, rather than the back-of-hand median.
  pad_ids=[];pad_goal=[]
  for d,ids in digit_groups.items():
   pts=skin.skin(pose,ids);_,_,dist=surface.nearest(pts);selected=ids[np.argsort(dist)[:min(16,max(6,len(ids)//12))]]
   pad_ids.extend(selected.tolist());pad_goal.extend([.12]*len(selected))
  pad_ids=np.array(pad_ids,int);base_points=skin.skin(pose,pad_ids)
  # Include the posed receiver at late insertion as a separate fit constraint.
  # Its space changes relative to the travelling magazine, so a static gun-space
  # box would be wrong during the reload.
  kind=donor_key.removeprefix('old_');source=json.load(gzip.open(I/('base__'+kind+'.json.gz'),'rt',encoding='utf8'))
  source_world=matrices(source['world']);source_bi={n:i for i,n in enumerate(source['bones'])}
  sample_frames=[8] if donor_key.startswith('old_') else ([43,70,80] if kind=='reload_empty' else [61,88,95])
  body_surfaces=[]
  for frame in sample_frames:
   j=int(np.argmin(np.abs(np.array(source['times'])*60-frame)))
   root=source_world[j,source_bi['WPN_root']]@np.linalg.inv(rest[ni['WPN_root']])
   mag=source_world[j,source_bi['WPN_SOCKET_Magazine']]@np.linalg.inv(rest[ni['WPN_SOCKET_Magazine']])
   transform=np.linalg.inv(mag)@root;pts=native['pos']@transform[:3,:3].T+transform[:3,3]
   # Limit source construction to triangles around the visible hand volume.
   center=np.mean([m[:3,3] for m in nominal.values()],axis=0)
   keep=np.linalg.norm(pts[body_tris].mean(axis=1)-center,axis=1)<18.
   if keep.any():body_surfaces.append(Surface(pts,body_tris[keep]))
  contact_hand_ids=np.unique(np.r_[pad_ids,np.flatnonzero(dominant==ni['hand_l'])[::7]])
  clearance_points=skin.skin(pose,contact_hand_ids)
  def correction(x):
   m=np.eye(4);m[:3,:3]=R.from_rotvec(x[3:]).as_matrix();m[:3,3]=x[:3];return fh@m@np.linalg.inv(fh)
  def residual(x):
   m=correction(x);pts=base_points@m[:3,:3].T+m[:3,3];q,n,dist=surface.nearest(pts)
   palm=clearance_points@m[:3,:3].T+m[:3,3]
   clearance=[np.maximum(.18-body.nearest(palm)[2],0.)*2. for body in body_surfaces]
   return np.r_[dist-np.array(pad_goal),*clearance,x[:3]*.25,x[3:]*2.]
  opt=least_squares(residual,np.zeros(6),bounds=([-0.8]*3+[-np.deg2rad(8)]*3,[0.8]*3+[np.deg2rad(8)]*3),max_nfev=65)
  corr=correction(opt.x);nominal={n:corr@m for n,m in nominal.items()}
  # Keep native finger translations and scales. Only donor rotations define the
  # natural wrap; hierarchy rebuild prevents stretch during pose transitions.
  localrots={n:(np.linalg.inv(nominal[names[parents[ni[n]]]])@nominal[n])[:3,:3] for n in HAND if n!='hand_l'}
  targets[donor_key]=(nominal['hand_l'],localrots)
  report['grips'][donor_key]={'source':source_info,'target':target_info,'translation_shell_cm':opt.x[:3].tolist(),'rotation_shell_deg':np.rad2deg(opt.x[3:]).tolist(),'receiver_clearance_target_cm':.18,'receiver_context_frames':sample_frames}
 for key,spec in index['clips'].items():
  kind=spec['kind']
  if kind not in ('reload','reload_empty'):continue
  with gzip.open(spec['file'],'rt',encoding='utf8') as f:source=json.load(f)
  sb=source['bones'];bi={n:i for i,n in enumerate(sb)};world=matrices(source['world']);local=matrices(source['local']);mag=ni['WPN_SOCKET_Magazine']
  arm=[n for n in sb if n.endswith('_l') and n.startswith(('clavicle','upperarm','lowerarm'))]
  tracknames=arm+HAND;tracks={n:[] for n in tracknames}
  for i,t in enumerate(source['times']):
   frame=t*60.;empty=kind=='reload_empty';oldw=smooth(2,7,frame)*(1-smooth(10,15 if empty else 21,frame))
   neww=smooth(35 if empty else 43,43 if empty else 61,frame)*(1-smooth(80 if empty else 95,100 if empty else 108,frame))
   w=max(oldw,neww);p=rest.copy()
   for n in sb:p[ni[n]]=world[i,bi[n]]
   if w>1e-8:
    wrist,rots=targets[('old_' if oldw>neww else '')+kind];D=p[mag]@np.linalg.inv(rest[mag]);hand=mix(p[ni['hand_l']],D@wrist,w)
    p=solve_arm(p,hand,names,ni)
    for n in HAND[1:]:
     j=ni[n];m=local[i,bi[n]].copy();r0=R.from_matrix(m[:3,:3]/np.linalg.norm(m[:3,:3],axis=0));r1=R.from_matrix(rots[n]);q=Slerp([0,1],R.from_quat([r0.as_quat(),r1.as_quat()]))([w]).as_matrix()[0]
     m[:3,:3]=q*np.array(source['local'][i][bi[n]][7:10]);p[j]=p[parents[j]]@m
   for n in tracknames:
    j=ni[n];original=source['local'][i][bi[n]]
    if w<=1e-8:row=original.copy()
    else:row=packed(np.linalg.inv(p[parents[j]])@p[j],original)
    if tracks[n] and np.dot(row[3:7],tracks[n][-1][3:7])<0:row[3:7]=(-np.array(row[3:7])).tolist()
    tracks[n].append(row)
  targets_spec={'source_sha256':spec['sha256'],'family':spec['family'],'kind':kind,'tracks':tracks}
  report['clips'][key]={'keys':len(source['times']),'seconds':source['seconds'],'old_contact_window_frames':[2,7,10,15 if empty else 21],'new_contact_window_frames':[35,43,80,100] if empty else [43,61,95,108]}
  yield key,targets_spec,report

if __name__=='__main__':
 clips={};report=None
 for key,spec,report in main():clips[key]=spec;print('HK416_STANDARD_GRIP_AUTHORED',spec['family'],spec['kind'],flush=True)
 with gzip.open(O/'standard_tracks.json.gz','wt',encoding='utf8') as f:json.dump({'clips':clips},f,separators=(',',':'))
 (O/'standard_authoring.json').write_text(json.dumps(report,indent=1))
