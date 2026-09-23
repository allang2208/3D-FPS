from pathlib import Path
import json,numpy as np
from PIL import Image
O=Path(__file__).parent;R=O.parent;T=O/'Textures';T.mkdir(exist_ok=True)
uv=np.load(O/'receiver_patch_uv.npy');report={}
for channel in ['BaseColor','ORM']:
 src=R/'Bipod07/Textures'/('T_PKM_QBZ_Body_'+channel+'.png')
 im=np.array(Image.open(src).convert('RGB'),dtype=np.float64);h,w=im.shape[:2]
 x=np.clip(uv[:,:,0]*w-.5,0,w-1);y=np.clip((1-uv[:,:,1])*h-.5,0,h-1)
 x0=x.astype(int);y0=y.astype(int);x1=np.minimum(x0+1,w-1);y1=np.minimum(y0+1,h-1)
 dx=(x-x0)[...,None];dy=(y-y0)[...,None]
 sample=(im[y0,x0]*(1-dx)+im[y0,x1]*dx)*(1-dy)+(im[y1,x0]*(1-dx)+im[y1,x1]*dx)*dy
 sample=np.flipud(sample).round().astype('uint8')
 if channel=='ORM':sample[:,:,0]=255
 out=T/('T_PKM23_Metal_'+channel+'.png');Image.fromarray(sample).save(out)
 report[channel]={'source':str(src),'output':str(out),'mean_byte':sample.mean(axis=(0,1)).tolist()}
normal=np.full((512,512,3),(128,128,255),dtype='uint8')
Image.fromarray(normal).save(T/'T_PKM23_Metal_Normal.png')
(O/'finish_sampling.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
