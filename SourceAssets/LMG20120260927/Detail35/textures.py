"""Clean only the coherent receiver panels in the existing UV atlas."""
import json,numpy as np
from pathlib import Path
from PIL import Image,ImageDraw,ImageFilter
from scipy.ndimage import gaussian_filter
O=Path(__file__).parent;T=O/'Textures';T.mkdir(exist_ok=True)
base=np.asarray(Image.open(O.parent/'Surface32/Textures/T_LMG201_S32_BaseColor.png').convert('RGB')).astype(np.float32)/255
orm=np.asarray(Image.open(O.parent/'Surface32/Textures/T_LMG201_S32_ORM.png').convert('RGB')).astype(np.float32)/255
normal=np.asarray(Image.open(O.parent/'Refine29/Textures/T_201_R29_Surface_Normal.png').convert('RGB')).astype(np.float32)/255
h,w=base.shape[:2];mask=Image.new('L',(w,h));draw=ImageDraw.Draw(mask)
src=np.load(O.parent/'Surface32/Work/Receiver.npz');edited=np.load(O/'Work/Receiver.npz');uv=src['uv'][src['loops']];strength=edited['flatmask'][src['faces']].mean(1)
for tri,alpha,mi in zip(uv,strength,src['material_ids']):
 if mi==0 and alpha>.12:
  draw.polygon([(float(p[0]*w),float((1-p[1])*h)) for p in tri],fill=int(alpha*255))
mask=mask.filter(ImageFilter.GaussianBlur(2));mask.save(T/'ReceiverPanelMask.png');a=np.asarray(mask).astype(np.float32)/255
# Keep local structural slopes and high-contrast stamped detail. Discard only
# short-wavelength variation in the already planar panel interiors.
nv=normal*2-1;blur=np.stack([gaussian_filter(nv[:,:,i],1.25) for i in range(3)],2)
edge=np.sqrt(sum(gaussian_filter(nv[:,:,i],.7,order=(1,0))**2+gaussian_filter(nv[:,:,i],.7,order=(0,1))**2 for i in [0,1]))
structure=np.clip((edge-.075)/.18,0,1);mix=a*.86*(1-structure)
nv=nv*(1-mix[:,:,None])+blur*mix[:,:,None];nv/=np.maximum(np.linalg.norm(nv,axis=2,keepdims=True),1e-8)
# Small tonal smoothing on broad panels. Printed markings and sharp features
# retain their local contrast rather than being painted with a flat color.
soft=np.stack([gaussian_filter(base[:,:,i],1.1) for i in range(3)],2);contrast=np.max(abs(base-soft),2)
color_mix=a*.50*(1-np.clip(contrast/.10,0,1));base=base*(1-color_mix[:,:,None])+soft*color_mix[:,:,None]
rough=orm[:,:,1];smooth=gaussian_filter(rough,1.5);orm[:,:,1]=rough*(1-a*.7)+np.clip(smooth,.54,.74)*a*.7
for kind,arr in [('BaseColor',base),('Normal',nv*.5+.5),('ORM',orm)]:
 Image.fromarray(np.clip(arr*255+.5,0,255).astype('uint8')).save(T/('T_LMG201_D35_Receiver_'+kind+'.png'))
(O/'textures.json').write_text(json.dumps({'source':'Surface32 color/ORM and Refine29 tangent normal','region':'current receiver coherent panel interiors only','uv':'original UV0 unchanged','normal_green_flip':False,'precision_parts':'dedicated plain coating; no old generated atlas normal'},indent=2))
print('DETAIL35_LOCAL_TEXTURES_SAVED',flush=True)
