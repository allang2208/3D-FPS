"""Pack source occlusion and a narrow normal-bevel edge mask for WS1.1."""
from pathlib import Path
from PIL import Image
import numpy as np,json
O=Path(__file__).resolve().parent;S=O.parent/'M24CustomScope20261026/Original/GLTF/textures';R={}
for group,stem in [('Body','sniper'),('Scope','Scope.002')]:
    orm=np.asarray(Image.open(S/(stem+'_metallicRoughness.png')).convert('RGB'),dtype=np.float32)/255
    old=np.asarray(Image.open(S/(stem+'_normal.png')).convert('RGB'),dtype=np.float32)/255
    new=np.asarray(Image.open(O/'Textures'/('T_M24_'+group+'_Refined_N.png')).convert('RGB'),dtype=np.float32)/255
    edge=np.clip(np.linalg.norm(new[...,:2]-old[...,:2],axis=2)*2,0,.45)
    ao=orm[...,0]
    # Keep the source AO as its own channel: only the standard AO stage consumes it.
    out=np.stack([edge,1-ao,ao,np.zeros_like(ao)],axis=2)
    path=O/'Textures'/('T_M24_'+group+'_SurfaceMask.png');Image.fromarray(np.round(out*255).astype('uint8'),'RGBA').save(path)
    R[group]={'source_occlusion':str(S/(stem+'_metallicRoughness.png')),'source_channel':'R','packed_channels':'R restrained bevel edge; G cavity; B AO; A handling=0','file':str(path)}
(O/'mask_recipe.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
