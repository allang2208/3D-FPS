"""Compare the saved near-camera geometry with the untouched GLB, including the chin."""
import json,struct,hashlib
import numpy as np
from pathlib import Path
from scipy.spatial import cKDTree
N=Path('D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115');R=N/'FaceOriginalRestoreR6'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
raw=(N/'MeshyHeadR1/Source/NunHead_R1_glb.glb').read_bytes();size=struct.unpack_from('<I',raw,12)[0];gltf=json.loads(raw[20:20+size]);base=28+size
a=gltf['accessors'][gltf['meshes'][0]['primitives'][0]['attributes']['POSITION']];v=gltf['bufferViews'][a['bufferView']]
p=np.ndarray((a['count'],3),dtype='<f4',buffer=raw,offset=base+v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',12),4))
p=p[:,[0,2,1]].astype(float)*15.8+[0,1.4,168.0523223876953-.94961101*15.8];tree=cKDTree(p)
out={'original_glb_sha256':hashlib.sha256(raw).hexdigest(),'comparisons':{},'runtime_pose_scope':'Actual NPC offscreen idle captures; no interactive gameplay or physics stress test'}
for label,file in [('authored','Authored/head.json'),('saved_source','EngineReadback/source_lod0_lowerface.json'),('render_lod0','EngineReadback/render_lod0_lowerface.json')]:
 d=read(R/file);ps=np.array(d['positions']);ps=ps[ps[:,2]>=142.5];dist,_=tree.query(ps)
 out['comparisons'][label]={'vertices':len(ps),'max_error_cm':float(dist.max()),'vertices_over_0_01mm':int((dist>.001).sum())}
 if np.any(dist>.001):raise RuntimeError('Original geometry drift '+label)
 for name,mask in [('chin',(ps[:,2]<149.2)&(ps[:,1]>4.7)&(np.abs(ps[:,0])<5.2)),('mouth',(ps[:,2]>149.2)&(ps[:,2]<153)&(ps[:,1]>6.5)&(np.abs(ps[:,0])<3.3))]:
  out['comparisons'][label][name]={'vertices':int(mask.sum()),'max_error_cm':float(dist[mask].max()) if mask.any() else 0}
engine=read(R/'EngineReadback/engine_readback.json');out['lod_settings']=[{'lod':x['lod'],'recompute_normals_disabled':'bRecomputeNormals=False' in x['build'],'full_precision_uv':'bUseFullPrecisionUVs=True' in x['build'],'triangles':x['triangles']} for x in engine['lods'] if x['type']=='render']
if not all(x['recompute_normals_disabled'] and x['full_precision_uv'] for x in out['lod_settings']):raise RuntimeError('LOD build policy did not persist')
(R/'original_face_verified.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out),flush=True)
