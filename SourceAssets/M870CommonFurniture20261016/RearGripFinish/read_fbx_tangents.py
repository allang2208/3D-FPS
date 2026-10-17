import json,numpy as np
from pathlib import Path
from io_scene_fbx import parse_fbx
O=Path(__file__).parent;R={}
for k in ('phantom_reargrip','stable_antislip_reargrip','balanced_reargrip'):
 root,version=parse_fbx.parse(str(O.parent/'Meshes'/('SM_M870_'+k+'.fbx')));row={}
 def walk(e):
  if e.id in (b'LayerElementTangent',b'LayerElementBinormal',b'LayerElementNormal'):
   for a in e.elems:
    if a.id in (b'Tangents',b'Binormals',b'Normals'):
     v=np.array(a.props[0]).reshape(-1,3);row[a.id.decode()]={'count':len(v),'zero':int(np.sum(np.all(np.abs(v)<1e-4,axis=1))),'nonfinite':int(np.sum(~np.isfinite(v))),'min_length':float(np.min(np.linalg.norm(v,axis=1)))}
  for c in e.elems:walk(c)
 walk(root);R[k]=row;print('FBX_TANGENTS',k,row,flush=True)
(O/'fbx_tangents.json').write_text(json.dumps(R,indent=2))
