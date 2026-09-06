"""Compare every GLB animation sampler with V01 and prepare deformation checks."""
from pathlib import Path
import json,struct
import numpy as np
R=Path(__file__).resolve().parent
def glb(path):
 data=path.read_bytes();pos=12;doc=None;binary=None
 while pos<len(data):
  size,kind=struct.unpack_from('<II',data,pos);chunk=data[pos+8:pos+8+size];pos+=8+size
  if kind==0x4e4f534a:doc=json.loads(chunk)
  elif kind==0x004e4942:binary=chunk
 return doc,binary
def accessor(doc,data,index):
 a=doc['accessors'][index];v=doc['bufferViews'][a['bufferView']]
 dims={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
 dt={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']]
 offset=v.get('byteOffset',0)+a.get('byteOffset',0)
 size=np.dtype(dt).itemsize
 return np.ndarray((a['count'],dims),dtype=dt,buffer=data,offset=offset,strides=(v.get('byteStride',dims*size),size)).copy()
def motions(doc,data):
 out={}
 for a in doc['animations']:
  channels={}
  for c in a['channels']:
   name=doc['nodes'][c['target']['node']]['name'];path=c['target']['path'];sampler=a['samplers'][c['sampler']]
   channels[(name,path)]=(accessor(doc,data,sampler['input']),accessor(doc,data,sampler['output']))
  out[a['name']]=channels
 return out
checks={}
for kind in ['modern','miner','runner']:
 old=R.parent/'modern-zombie-v01-20260906/modern-zombie-v01.glb' if kind=='modern' else R.parent/'humanoid-variants-v01-20260906'/kind/(kind+'-zombie-v01.glb')
 new=R/kind/(kind+'-zombie-v02.glb')
 d0,b0=glb(old);d1,b1=glb(new)
 a0=motions(d0,b0);a1=motions(d1,b1);assert a0.keys()==a1.keys()
 error=0.;tracks=0
 for name in a0:
  assert a0[name].keys()==a1[name].keys(),(kind,name)
  for channel in a0[name]:
   for before,after in zip(a0[name][channel],a1[name][channel]):
    assert before.shape==after.shape,(kind,name,channel,before.shape,after.shape)
    error=max(error,float(np.max(np.abs(before-after))))
   tracks+=1
 assert error<1e-5,(kind,error)
 checks[kind]={'clips':len(a1),'tracks':tracks,'maximum_sampler_difference':error,'bone_count':len(d1['skins'][0]['joints'])}
 test=(R.parent/'modern-zombie-v01-20260906/check_model.py').read_text().replace("R/'modern-zombie-v01.glb'",f"R/'{kind}-zombie-v02.glb'")
 (R/kind/'check_model.py').write_text(test,encoding='utf8')
(R/'animation-parity.json').write_text(json.dumps(checks,indent=2),encoding='utf8')
print('ANIMATION_PARITY_PASS',json.dumps(checks))
