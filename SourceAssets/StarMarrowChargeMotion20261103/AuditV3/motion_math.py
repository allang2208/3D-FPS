import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.ndimage import gaussian_filter1d
from pathlib import Path
import json
P=Path(__file__).resolve().parent
rig=json.loads((P/'rig.json').read_text());native=json.loads((P.parent/'AuditV2/NativeFinal/Standard/surface.json').read_text(encoding='utf-8-sig'))
names=rig['names'];parents=rig['parents'];rest={n:np.array(m) for n,m in rig['rest'].items()}
def unit(v):return v/max(np.linalg.norm(v),1e-12)
def rotation(m):return m[:3,:3]/np.linalg.norm(m[:3,:3],axis=0)
def mat(v):
 m=np.eye(4);m[:3,:3]=R.from_quat(v['q']).as_matrix()*v['s'];m[:3,3]=v['p'];return m
nrest={n:mat(v) for n,v in zip(native['bone_names'],native['rest'])}
A=np.diag([.01,-.01,.01,1]);AI=np.linalg.inv(A)
def read_variant(variant):
 d=json.loads((P/'installed.json').read_text());raw=d['variants'][variant]
 def convert(local):
  w={}
  for n,v in zip(d['names'],local):w[n]=w.get(d['parents'][n],np.eye(4))@mat(v)
  return {n:A@w[n]@np.linalg.inv(nrest[n])@AI@rest[n] for n in names}
 return convert(raw['idle']),[convert(row) for row in raw['frames']]
def frame(x,z):
 x=unit(x);z=unit(z-x*(z@x));return np.column_stack([x,np.cross(z,x),z])
def axis_angle(axis,angle):return R.from_rotvec(unit(axis)*angle).as_matrix()
def twist(D,axis):
 q=R.from_matrix(D).as_quat();t=2*np.arctan2(q[:3]@unit(axis),q[3]);return (t+np.pi)%(2*np.pi)-np.pi

def smooth(x,sigma):return gaussian_filter1d(np.array(x,float),sigma,axis=0,mode='nearest')
def make(p,q,scale):
 m=np.eye(4);m[:3,:3]=q*scale;m[:3,3]=p;return m
