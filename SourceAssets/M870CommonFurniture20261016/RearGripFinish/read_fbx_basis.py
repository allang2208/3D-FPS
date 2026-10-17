import json,numpy as np
from pathlib import Path
from io_scene_fbx import parse_fbx
O=Path(__file__).parent;R={}
for k in ('phantom_reargrip','stable_antislip_reargrip','balanced_reargrip'):
 root,_=parse_fbx.parse(str(O.parent/'Meshes'/('SM_M870_'+k+'.fbx')));d={}
 def walk(e):
  if e.id in (b'LayerElementTangent',b'LayerElementBinormal',b'LayerElementNormal'):
   for c in e.elems:
    if c.id in (b'Tangents',b'Binormals',b'Normals',b'NormalsIndex'):d[c.id.decode()]=np.array(c.props[0])
  for c in e.elems:walk(c)
 walk(root)
 n=d['Normals'].reshape(-1,3)[d['NormalsIndex']];t=d['Tangents'].reshape(-1,3);b=d['Binormals'].reshape(-1,3)
 nt=np.abs(np.sum(n*t,axis=1));cross=np.linalg.norm(np.cross(n,t),axis=1)
 R[k]={'max_normal_tangent_dot':float(max(nt)),'parallel_NT':int(np.sum(cross<1e-4)),'bad_corners':np.flatnonzero(cross<1e-4).tolist(),'max_normal_binormal_dot':float(max(np.abs(np.sum(n*b,axis=1))))};print(k,R[k],flush=True)
(O/'fbx_basis.json').write_text(json.dumps(R,indent=2))
