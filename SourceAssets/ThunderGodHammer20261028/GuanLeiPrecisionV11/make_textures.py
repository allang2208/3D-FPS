from pathlib import Path
import numpy as np
from PIL import Image,ImageFilter
P=Path(__file__).resolve().parent/'Textures';P.mkdir(exist_ok=True)
N=2048;rng=np.random.default_rng(731)
def field(n,blur=0):
 im=Image.fromarray(rng.integers(0,256,(n,n),dtype=np.uint8)).resize((N,N),Image.Resampling.BICUBIC)
 if blur:im=im.filter(ImageFilter.GaussianBlur(blur))
 return np.asarray(im,dtype=np.float32)/255
cloud=field(64,3);grain=field(512,2);fine=field(1024,1)
height=(grain-.5)*.000002+(fine-.5)*.0000008
dy,dx=np.gradient(height,.055/N);normal=np.stack((-dx,-dy,np.ones_like(dx)),axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
Image.fromarray(np.uint8(np.clip(normal*.5+.5,0,1)*255)).save(P/'T_GuanLei11_Metal_Normal.png')
for name,base,rough in [('Steel',(.19,.205,.22),.54),('Silver',(.47,.46,.42),.35),('Recess',(.13,.15,.17),.57),('Inlay',(.50,.49,.45),.36)]:
 variation=.93+.10*cloud+.025*(fine-.5);rgb=np.array(base)[None,None,:]*variation[:,:,None]
 Image.fromarray(np.uint8(np.clip(rgb,0,1)*255)).save(P/('T_GuanLei11_'+name+'_BaseColor.png'))
 orm=np.stack((np.ones_like(cloud),np.clip(rough+.07*(cloud-.5)+.025*(grain-.5),0,1),np.ones_like(cloud)*.95),axis=-1)
 Image.fromarray(np.uint8(orm*255)).save(P/('T_GuanLei11_'+name+'_ORM.png'))
print('PBR_MAPS_WRITTEN',flush=True)
