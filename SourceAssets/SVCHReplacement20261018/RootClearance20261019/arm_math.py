import json,gzip
import numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation as R,Slerp
O=Path(__file__).parent
load=lambda n:json.load(gzip.open(O/'Inputs'/(n+'.json.gz'),'rt'))
motion=load('motion');arms=load('arms');weapon=load('svch')
names=motion['names'];ids={n:i for i,n in enumerate(names)};parents=[ids.get(n,-1) for n in motion['parents']]
profile=json.loads((O/'Inputs/profile_before.json').read_text())
def matrices(v):
 a=np.asarray(v);m=np.zeros(a.shape[:-1]+(4,4));m[...,3,3]=1;m[...,:3,3]=a[...,:3]
 m[...,:3,:3]=R.from_quat(a[...,3:7].reshape(-1,4)).as_matrix().reshape(a.shape[:-1]+(3,3))*a[...,None,7:10]
 return m
def rigid(m):
 a=m.copy();a[...,:3,:3]/=np.linalg.norm(a[...,:3,:3],axis=-2)[...,None,:];return a
def comp(m):
 a=m.copy()
 for i,p in enumerate(parents):
  if p>=0:
   parent=a[p];child=a[i].copy();ps=np.linalg.norm(parent[:3,:3],axis=0);cs=np.linalg.norm(child[:3,:3],axis=0)
   a[i,:3,3]=parent[:3,:3]@child[:3,3]+parent[:3,3]
   # UE FTransform composes quaternion + component scale, not a sheared matrix.
   a[i,:3,:3]=((parent[:3,:3]/ps)@(child[:3,:3]/cs))*(ps*cs)
 return a
def relative(parent,child):
 ps=np.linalg.norm(parent[:3,:3],axis=0);cs=np.linalg.norm(child[:3,:3],axis=0);rp=parent[:3,:3]/ps;rc=child[:3,:3]/cs
 a=np.eye(4);a[:3,3]=(rp.T@(child[:3,3]-parent[:3,3]))/ps;a[:3,:3]=(rp.T@rc)*(cs/ps)
 return a
def sample(t,track):
 ts=np.asarray(track['times']);v=np.asarray(track['values']).reshape(-1,10)
 if len(ts)==1:return v[0]
 j=int(np.clip(np.searchsorted(ts,t)-1,0,len(ts)-2));w=float(np.clip((t-ts[j])/(ts[j+1]-ts[j]),0,1));out=(1-w)*v[j]+w*v[j+1]
 out[3:7]=Slerp([0,1],R.from_quat(v[j:j+2,3:7]))([w]).as_quat()[0];return out
def apply(base,layer,t):
 a=np.asarray(base).copy()
 for track in layer['tracks']:
  i=ids[track['bone']];d=sample(t,track)
  a[i,:3]+=d[:3];a[i,7:]+=d[7:];a[i,3:7]=(R.from_quat(d[3:7])*R.from_quat(a[i,3:7])).as_quat()
 return a
def pose(role,index,p=profile):
 c=motion['clips'][role];layer=next(x for x in p['clips'] if x['base']==c['path'])
 return comp(matrices(apply(c['frames'][index],layer,c['times'][index])))
def unit(v):return v/max(np.linalg.norm(v),1e-12)
def swing(a,b):
 a,b=unit(a),unit(b);x=np.cross(a,b);l=np.linalg.norm(x)
 return np.eye(3) if l<1e-10 else R.from_rotvec(x/l*np.arctan2(l,np.clip(a@b,-1,1))).as_matrix()
def aimed(old,oldend,start,end):
 m=old.copy();m[:3,:3]=swing(oldend-old[:3,3],end-start)@old[:3,:3];m[:3,3]=start;return m
def ease(a,b,t):
 x=np.clip((t-a)/(b-a),0,1);return x*x*x*(10-15*x+6*x*x)
V=np.asarray(arms['positions']);W=np.zeros((len(V),len(names)))
for i,row in enumerate(arms['weights']):
 for b,w in row:W[i,ids[arms['weight_bones'][b]]]=w
inv=np.linalg.inv(matrices(arms['reference']));dom=W.argmax(1)
left=np.flatnonzero([names[b].endswith('_l') for b in dom])
upper=np.flatnonzero([names[b].startswith(('clavicle','upperarm')) and names[b].endswith('_l') for b in dom])
lower=np.flatnonzero([names[b].startswith('lowerarm') and names[b].endswith('_l') for b in dom])
hand=np.flatnonzero([names[b].startswith(('hand','thumb','index','middle','ring','pinky')) and names[b].endswith('_l') for b in dom])
def skin(p,selected):
 result=np.zeros((len(selected),3))
 for b in np.flatnonzero(W[selected].max(0)>0):
  m=p[b]@inv[b];result+=(V[selected]@m[:3,:3].T+m[:3,3])*W[selected,b,None]
 return result
def camera_transform(loc,rot):
 m=np.eye(4);m[:3,:3]=R.from_euler('xyz',[-rot[0],-rot[1],rot[2]],degrees=True).as_matrix();m[:3,3]=loc;return m
def transform(m,v):return np.asarray(v)@m[:3,:3].T+m[:3,3]
