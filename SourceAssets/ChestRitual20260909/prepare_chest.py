import json,struct,copy,hashlib
from pathlib import Path
import numpy as np
out=Path(__file__).parent
src=out/'warehouse_chest_ritual_v8.glb'
b=src.read_bytes();n=struct.unpack_from('<I',b,12)[0];d=json.loads(b[20:20+n]);off=20+n;size=struct.unpack_from('<I',b,off)[0];blob=bytearray(b[off+8:off+8+size])
types={5126:'<f4',5123:'<u2',5125:'<u4',5121:'u1'};dims={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
def read(i):
 a=d['accessors'][i];v=d['bufferViews'][a['bufferView']];dt=np.dtype(types[a['componentType']]);start=v.get('byteOffset',0)+a.get('byteOffset',0);count=a['count'];width=dims[a['type']]
 return np.ndarray((count,width),dtype=dt,buffer=blob,offset=start,strides=(v.get('byteStride',dt.itemsize*width),dt.itemsize)).copy()
def add(arr,kind,component=5126):
 arr=np.asarray(arr,dtype=types[component]);blob.extend(b'\0'*((-len(blob))%4));offset=len(blob);raw=arr.tobytes();blob.extend(raw);view=len(d['bufferViews']);d['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(raw)})
 a={'bufferView':view,'componentType':component,'count':len(arr),'type':kind}
 if kind=='VEC3':a.update(min=arr.min(axis=0).tolist(),max=arr.max(axis=0).tolist())
 idx=len(d['accessors']);d['accessors'].append(a);return idx
parents={c:i for i,node in enumerate(d['nodes']) for c in node.get('children',[])}
def local(node):
 if 'matrix' in node:return np.array(node['matrix']).reshape(4,4).T
 x,y,z,w=node.get('rotation',[0,0,0,1]);r=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
 m=np.eye(4);m[:3,:3]=r@np.diag(node.get('scale',[1,1,1]));m[:3,3]=node.get('translation',[0,0,0]);return m
def world(i):return (world(parents[i]) if i in parents else np.eye(4))@local(d['nodes'][i])
matrices=[world(i) for i in range(len(d['nodes']))];prims=[]
for i,node in enumerate(d['nodes']):
 if 'mesh' not in node:continue
 for source in d['meshes'][node['mesh']]['primitives']:
  p=copy.deepcopy(source);a=p['attributes'];pos=read(a['POSITION']);positions=np.c_[pos,np.ones(len(pos))]@matrices[i].T;a['POSITION']=add(positions[:,:3],'VEC3')
  if 'NORMAL' in a:
   normal=read(a['NORMAL'])@np.linalg.inv(matrices[i][:3,:3]);normal/=np.linalg.norm(normal,axis=1)[:,None];a['NORMAL']=add(normal,'VEC3')
  a.pop('TANGENT',None);j=np.zeros((len(pos),4),dtype=np.uint16);j[:,0]=i;w=np.zeros((len(pos),4));w[:,0]=1;a['JOINTS_0']=add(j,'VEC4',5123);a['WEIGHTS_0']=add(w,'VEC4');prims.append(p)
 node.pop('mesh')
d['meshes']=[{'name':'WarehouseChestRigid','primitives':prims}]
d['skins']=[{'name':'WarehouseSourceRig','joints':list(range(len(matrices))),'skeleton':4,'inverseBindMatrices':add(np.array([np.linalg.inv(m).T.flatten() for m in matrices]),'MAT4')}]
d['nodes'].append({'name':'WarehouseChestRigidMesh','mesh':0,'skin':0});d['scenes']=[{'nodes':[4,5]}];d['scene']=0
blob.extend(b'\0'*((-len(blob))%4));d['buffers']=[{'byteLength':len(blob)}];raw=json.dumps(d,separators=(',',':')).encode();raw+=b' '*((-len(raw))%4)
(out/'warehouse_chest_rigid.glb').write_bytes(struct.pack('<III',0x46546c67,2,28+len(raw)+len(blob))+struct.pack('<II',len(raw),0x4e4f534a)+raw+struct.pack('<II',len(blob),0x004e4942)+blob)
report={'source':str(src),'sha256':hashlib.sha256(b).hexdigest(),'vertices':sum(d['accessors'][p['attributes']['POSITION']]['count'] for p in prims),'joints':len(matrices),'animations':[{'name':a['name'],'channels':len(a['channels']),'duration':max(float(read(s['input']).max()) for s in a['samplers'])} for a in d['animations']],'contract':'Source animation channels and hierarchy retained verbatim; rigid weighting only. Open 0.9 s; Close 0.7 s; no looping.'}
(out/'source_contract.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
