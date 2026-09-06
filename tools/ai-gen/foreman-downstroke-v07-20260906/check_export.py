"""Check actual exported whip skin at every 1/160s, including key midpoints."""
import json,struct,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
source=ROOT/(sys.argv[1] if len(sys.argv)>1 else 'foreman-downstroke-v07.glb')
raw=source.read_bytes();off=12
while off<len(raw):
 size,kind=struct.unpack_from('<II',raw,off);chunk=raw[off+8:off+8+size];off+=8+size
 if kind==0x4e4f534a:doc=json.loads(chunk)
 elif kind==0x004e4942:blob=chunk
def read(idx):
 a=doc['accessors'][idx];v=doc['bufferViews'][a['bufferView']];dt=np.dtype({5126:'<f4',5123:'<u2',5121:'u1',5125:'<u4'}[a['componentType']]);n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
 return np.ndarray((a['count'],n),dtype=dt,buffer=blob,offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',n*dt.itemsize),dt.itemsize)).copy()
def trs(t,q,s):
 x,y,z,w=q/np.linalg.norm(q);m=np.eye(4);m[:3,:3]=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])@np.diag(s);m[:3,3]=t;return m
nodes=doc['nodes'];parents={c:i for i,n in enumerate(nodes) for c in n.get('children',[])}
hand=next(i for i,n in enumerate(nodes) if n.get('name')=='hand.R')
whips=[i for i,n in enumerate(nodes) if n.get('name','').startswith('whip.')]
assert len(whips)==33 and all(parents[i]==hand for i in whips)
mi=next(i for i,n in enumerate(nodes) if n.get('name')=='Whip');sn=doc['skins'][nodes[mi]['skin']];prim=doc['meshes'][nodes[mi]['mesh']]['primitives'][0];attrs=prim['attributes'];pos=read(attrs['POSITION']);pos=np.column_stack([pos,np.ones(len(pos))]);j=read(attrs['JOINTS_0']);weights=read(attrs['WEIGHTS_0']);assert np.allclose(weights.sum(axis=1),1)
ibm=read(sn['inverseBindMatrices']).reshape(-1,4,4).transpose(0,2,1)
report={'samples':0,'max_distance_from_hand_m':0.,'clips':{}}
for anim in doc['animations']:
 channels=[]
 for c in anim['channels']:
  sam=anim['samplers'][c['sampler']];channels.append((c['target']['node'],c['target']['path'],read(sam['input'])[:,0],read(sam['output'])))
 end=max(ch[2][-1] for ch in channels);report['clips'][anim['name']]=float(end)
 for t in np.linspace(0,end,round(end*160)+1):
  values={}
  for idx,path,times,vs in channels:
   k=min(len(times)-2,max(0,np.searchsorted(times,t)-1));u=np.clip((t-times[k])/max(1e-9,times[k+1]-times[k]),0,1);a=vs[k];b=vs[k+1]
   if path=='rotation' and np.dot(a,b)<0:b=-b
   values[idx,path]=a*(1-u)+b*u
  world={}
  def matrix(i):
   if i not in world:
    n=nodes[i];m=trs(values.get((i,'translation'),n.get('translation',[0,0,0])),values.get((i,'rotation'),n.get('rotation',[0,0,0,1])),values.get((i,'scale'),n.get('scale',[1,1,1])))
    if i in parents:m=matrix(parents[i])@m
    world[i]=m
   return world[i]
  skin=np.array([matrix(idx)@ibm[k] for k,idx in enumerate(sn['joints'])]);out=np.zeros((len(pos),4))
  for k in range(4):out+=np.einsum('nij,nj->ni',skin[j[:,k]],pos)*weights[:,k,None]
  dist=np.linalg.norm(out[:,:3]-matrix(hand)[:3,3],axis=1).max()
  assert np.isfinite(out).all() and dist<6.9,(anim['name'],t,dist)
  for idx in whips:assert np.allclose(values.get((idx,'scale'),nodes[idx].get('scale',[1,1,1])),1,atol=1e-4)
  report['samples']+=1;report['max_distance_from_hand_m']=max(report['max_distance_from_hand_m'],float(dist))
values={};world={}
bind_length=sum(np.linalg.norm(matrix(whips[i+1])[:3,3]-matrix(whips[i])[:3,3]) for i in range(32));assert abs(bind_length-6.4)<1e-4,bind_length
report['bind_centerline_m']=float(bind_length)
(ROOT/'export-validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
