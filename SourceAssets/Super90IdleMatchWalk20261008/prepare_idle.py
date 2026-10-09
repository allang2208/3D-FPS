"""Carry the installed walking left-arm hold in gun space through the idle cycle."""
import json,numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation,Slerp
O=Path(__file__).parent;D=json.loads((O/'inputs.json').read_text());names=D['names'];parents=D['parents']

def mat(v):
 m=np.eye(4);m[:3,:3]=Rotation.from_quat(v[3:7]).as_matrix()@np.diag(v[7:]);m[:3,3]=v[:3];return m

def pack(m):
 scale=np.linalg.norm(m[:3,:3],axis=0);r=m[:3,:3]/scale
 if np.linalg.det(r)<0:scale[0]*=-1;r[:,0]*=-1
 return np.r_[m[:3,3],Rotation.from_matrix(r).as_quat(),scale].tolist()

def world(row):
 w={}
 for n in names:w[n]=w.get(parents[n],np.eye(4))@mat(row[n])
 return w

def under(n,root):
 while n in parents:
  if n==root:return True
  n=parents[n]
 return False
left=[n for n in names if under(n,'clavicle_l')]

def delta_sample(track,t):
 times=np.array(track['times']);v=np.array(track['values']).reshape(-1,10)
 if len(times)==1 or t<=times[0]:return v[0]
 if t>=times[-1]:return v[-1]
 hi=np.searchsorted(times,t,side='right');lo=hi-1;a=(t-times[lo])/(times[hi]-times[lo]);r=(1-a)*v[lo]+a*v[hi]
 r[3:7]=Slerp([0,1],Rotation.from_quat(v[[lo,hi],3:7]))([a]).as_quat()[0];return r

def apply(row,clip,t):
 r={n:list(v) for n,v in row.items()}
 for track in clip['tracks']:
  n=track['bone'];v=np.array(r[n]);d=delta_sample(track,t)
  v[:3]+=d[:3];v[3:7]=(Rotation.from_quat(d[3:7])*Rotation.from_quat(v[3:7])).as_quat();v[7:]+=d[7:];r[n]=v.tolist()
 return r

def rehold(row,donor):
 w=world(row);move=w['WPN_root']@np.linalg.inv(donor['WPN_root'])
 for n in left:w[n]=move@donor[n]
 r={n:list(v) for n,v in row.items()}
 for n in left:r[n]=pack(np.linalg.inv(w[parents[n]])@w[n])
 return r

def track(n,values):
 a=np.array(values)
 for i in range(1,len(a)):
  if np.dot(a[i-1,3:7],a[i,3:7])<0:a[i,3:7]*=-1
 return {'bone':n,'times':times,'values':a.reshape(-1).tolist()}

times=[i*D['seconds']/D['frames'] for i in range(D['frames']+1)]
base_donor=world(D['walk']);rows=[rehold(r,base_donor) for r in D['idle_rows']]
out={'revision':'Super90IdleMatchWalk-20261008','idle_path':D['idle_path'],'walk_path':D['walk_path'],'duration':D['seconds'],'frames':D['frames'],'left_bones':left,'base_tracks':[track(n,[r[n] for r in rows]) for n in left],'profiles':{}}
for f,p in D['profiles'].items():
 idle=next(c for c in p['clips'] if c['base']==D['idle_path']);walk=next(c for c in p['clips'] if c['base']==D['walk_path'])
 if idle['retained']:raise RuntimeError('Idle retained override requires explicit authoring: '+f)
 donor=world(p['retained_walk'] if 'retained_walk' in p else apply(D['walk'],walk,0.))
 family_rows=[rehold(apply(old,idle,t),donor) for old,t in zip(D['idle_rows'],times)]
 tracks=[t for t in idle['tracks'] if t['bone'] not in left]
 for n in left:
  keys=[]
  for b,a in zip(rows,family_rows):
   bv=np.array(b[n]);av=np.array(a[n]);q=(Rotation.from_quat(av[3:7])*Rotation.from_quat(bv[3:7]).inv()).as_quat()
   keys.append(np.r_[av[:3]-bv[:3],q,av[7:]-bv[7:]].tolist())
  tracks.append(track(n,keys))
 out['profiles'][f]={'path':p['path'],'idle':{'base':D['idle_path'],'duration':D['seconds'],'tracks':tracks}}
(O/'idle_patch.json').write_text(json.dumps(out,separators=(',',':')),encoding='utf-8')
print('PREPARED_IDLE_LEFT_ARM',len(left),'bones',len(rows),'keys',len(out['profiles']),'grip families')
