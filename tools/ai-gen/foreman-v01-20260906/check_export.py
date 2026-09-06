import json,struct
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
raw=(ROOT/'foreman-preview.glb').read_bytes();offset=12;doc=None;binary=None
while offset<len(raw):
 size,kind=struct.unpack_from('<II',raw,offset);chunk=raw[offset+8:offset+8+size];offset+=8+size
 if kind==0x4e4f534a:doc=json.loads(chunk)
 elif kind==0x004e4942:binary=chunk
def accessor(index):
 a=doc['accessors'][index];v=doc['bufferViews'][a['bufferView']];types={5126:'<f4',5123:'<u2',5121:'u1',5125:'<u4'};dtype=np.dtype(types[a['componentType']]);cols={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']];return np.ndarray((a['count'],cols),dtype=dtype,buffer=binary,offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',cols*dtype.itemsize),dtype.itemsize))
report={'clips':{},'skins':len(doc.get('skins',[])),'joint_counts':[len(s['joints']) for s in doc['skins']],'meshes':[]}
for m in doc['meshes']:
 for prim in m['primitives']:
  attrs=prim['attributes'];w=accessor(attrs['WEIGHTS_0']);error=float(np.abs(w.sum(axis=1)-1).max());assert error<.0001
  assert 'NORMAL' in attrs
  report['meshes'].append({'name':m['name'],'vertices':len(w),'max_weights':int((w>0).sum(axis=1).max()),'weight_sum_error':error,'uv':'TEXCOORD_0' in attrs})
for anim in doc['animations']:
 times=[accessor(s['input']) for s in anim['samplers']];report['clips'][anim['name']]=float(max(t.max() for t in times)-min(t.min() for t in times))
expected={'Idle':1,'Walk':1.5,'Attack':1.5,'Howl':3,'Death':1.4}
for name,duration in expected.items():assert abs(report['clips'][name]-duration)<.001
(ROOT/'export-validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
