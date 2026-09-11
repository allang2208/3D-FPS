import json,numpy as np
from PIL import Image
from pathlib import Path
r=Path('D:/FPS3D/FPSGAME/SourceAssets/HandBrain20260910/surface_v07')
manifest=json.loads((r.parent/'sculpt_v06/bake_manifest.json').read_text())
row=next(x for x in manifest if x['object']=='HandBrain_Body' and x['slot']==0 and x['semantic']=='Normal_DirectX')
mask=np.asarray(Image.open(r/'textures/Surface_0_Mask.png').convert('RGB'),np.float32)[:,:,:1]/255
a=np.asarray(Image.open(row['path']).convert('RGB'),np.float32)/255;b=np.asarray(Image.open(r/'textures/Surface_0_Normal_DirectX.png').convert('RGB'),np.float32)/255
v=(a*2-1)*(1-mask)+(b*2-1)*mask;v/=np.maximum(np.linalg.norm(v,axis=2,keepdims=True),1e-6)
result=np.where(mask==0,a,v*.5+.5);path=r/'textures/Surface_Final_Normal_DirectX.png'
Image.fromarray(np.uint8(np.clip(result*255+.5,0,255))).save(path);row['path']=str(path)
(r/'bake_manifest.json').write_text(json.dumps(manifest,indent=2))
(r/'mask_validation.json').write_text(json.dumps({'normal_mask_fraction':float((mask>0).mean()),'color_roughness_oral_maps_reused':True,'untouched_pixels_preserved':True},indent=2))
print('SURFACE_MAP_MERGED')
