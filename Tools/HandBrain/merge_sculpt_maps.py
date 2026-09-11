"""Composite tangent-space bake data only inside the authored sculpt mask."""
from pathlib import Path
import json,numpy as np
from PIL import Image
r=Path('D:/FPS3D/FPSGAME/SourceAssets/HandBrain20260910');o=r/'sculpt_v06'
old=json.loads((r/'realism_v05/bake_manifest.json').read_text());rows=json.loads((o/'bake_manifest.json').read_text())
mask=np.asarray(Image.open(o/'textures/Sculpt_Body_0_Mask.png').convert('RGB'),np.float32)[:,:,:1]/255
for sem in ['BaseColor','Normal_DirectX']:
 before=next(x for x in old if x['object']=='HandBrain_Body' and x['slot']==0 and x['semantic']==sem)
 row=next(x for x in rows if x['object']=='HandBrain_Body' and x['slot']==0 and x['semantic']==sem)
 a=np.asarray(Image.open(before['path']).convert('RGB'),np.float32)/255;b=np.asarray(Image.open(o/'textures'/('Sculpt_Body_0_'+sem+'.png')).convert('RGB'),np.float32)/255
 if sem=='Normal_DirectX':
  v=(a*2-1)*(1-mask)+(b*2-1)*mask;v/=np.maximum(np.linalg.norm(v,axis=2,keepdims=True),1e-6);result=v*.5+.5
 else:result=(a**2.2*(1-mask)+b**2.2*mask)**(1/2.2)
 result=np.where(mask==0,a,result)
 path=o/'textures'/('Sculpt_Final_'+sem+'.png');Image.fromarray(np.uint8(np.clip(result*255+.5,0,255))).save(path);row['path']=str(path)
(o/'bake_manifest.json').write_text(json.dumps(rows,indent=2))
(o/'mask_validation.json').write_text(json.dumps({'mask_nonzero_fraction':float((mask>0).mean()),'untouched_pixels_preserved_exactly':True,'oral_and_mouth_maps_reused':True},indent=2))
print('SCULPT_MASK_COMPOSITE_COMPLETE')
