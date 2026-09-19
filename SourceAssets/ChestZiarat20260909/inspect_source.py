import json, struct, hashlib
from pathlib import Path
import numpy as np
from PIL import Image
root=Path(__file__).parent
b=Path('D:/FPS3D/FPSGAME/SourceAssets/WarehouseMigration20260909/warehouse_chest_rigid.glb').read_bytes()
n=struct.unpack_from('<I',b,12)[0];d=json.loads(b[20:20+n]);blob=b[28+n:]
def read(i):
 a=d['accessors'][i];v=d['bufferViews'][a['bufferView']];dt=np.dtype({5126:'<f4',5123:'<u2',5125:'<u4'}[a['componentType']]);w={'SCALAR':1,'VEC2':2,'VEC3':3}[a['type']]
 return np.ndarray((a['count'],w),dtype=dt,buffer=blob,offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',dt.itemsize*w),dt.itemsize)).copy()
meshes=[]
for m in d['meshes']:
 for p in m['primitives']:
  if d['materials'][p['material']]['name']!='White_Marble_PBR':continue
  pos=read(p['attributes']['POSITION']);uv=read(p['attributes']['TEXCOORD_0']);idx=read(p['indices']).flatten();tri=pos[idx].reshape(-1,3,3);tuv=uv[idx].reshape(-1,3,2)
  area=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)*.5
  ua=np.abs(np.cross(tuv[:,1]-tuv[:,0],tuv[:,2]-tuv[:,0]))*.5
  valid=(area>1e-8)&(ua>1e-8)
  meshes.append({'bounds_m':[pos.min(0).tolist(),pos.max(0).tolist()],'uv_range':[uv.min(0).tolist(),uv.max(0).tolist()],'median_uv_per_m':float(np.median(np.sqrt(ua[valid]/area[valid]))),'vertices':len(pos)})
textures=[]
for f in (root/'Source').rglob('*.jpg'):
 im=Image.open(f);arr=np.asarray(im)
 textures.append({'file':f.name,'size':im.size,'mean':arr.mean(axis=(0,1)).tolist(),'range':[arr.min(axis=(0,1)).tolist(),arr.max(axis=(0,1)).tolist()],'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
report={'marble_uv':meshes,'textures':textures}
(root/'source_report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
