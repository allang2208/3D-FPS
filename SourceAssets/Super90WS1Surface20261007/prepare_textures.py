"""Bake WS1 data inputs from the source atlas: clean receiver + protected ink, AO."""
import json,numpy as np
from PIL import Image
from pathlib import Path
O=Path(__file__).parent;T=O/'Textures';T.mkdir(exist_ok=True)
S=O.parent/'BenelliM4Super9020261006/Original/Source/textures'
base=np.asarray(Image.open(S/'TTI_Benelli_M4_BaseColor_brand_friendly.png').convert('RGB'),dtype=np.float32)/255
metal=np.asarray(Image.open(S/'TTI_Benelli_M4_Metallic_brand_friendly.png').convert('L'),dtype=np.float32)/255
ao=np.asarray(Image.open(S/'TTI_Benelli_M4_AO.png').convert('L'))
r,g,b=base[:,:,0],base[:,:,1],base[:,:,2]
# Author's white Benelli text and warm TTI inlays/lettering survive the new finish.
# Low-frequency atlas colour, dirt and polygon-shaped shading are not copied.
gold=(r>g*1.10)&(g>b*1.12)&(r>.28)
white=(base.min(axis=2)>.52)&((base.max(axis=2)-base.min(axis=2))<.09)&(metal<.5)
ink=gold|white
linear=np.array([.020,.021,.022],dtype=np.float32)
encoded=np.where(linear<=.0031308,12.92*linear,1.055*linear**(1/2.4)-.055)
clean=np.broadcast_to(encoded,base.shape).copy();clean[ink]=base[ink]
Image.fromarray(np.rint(np.clip(clean,0,1)*255).astype(np.uint8)).save(T/'T_Super90_CleanReceiver.png')
mask=np.zeros((*ao.shape,4),dtype=np.uint8);mask[:,:,2]=ao;mask[:,:,3]=255
Image.fromarray(mask).save(T/'T_Super90_SurfaceMask.png')
(O/'texture_recipe.json').write_text(json.dumps({'source':str(S),'color':'sRGB encoded; clean anodized receiver + original white/gold marking pixels only','mask':'linear RGBA = 0,0,source AO,1; UV0; no invented wear mask','normal':'existing UV0 OpenGL source texture; existing UE green-channel conversion retained','runtime_tested':False},indent=2))
print('SUPER90_WS1_TEXTURE_INPUTS_AUTHORED')
