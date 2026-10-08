"""Bake physically shallow inlay and satin steel maps from the authored mask."""
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, map_coordinates
P=Path(__file__).resolve().parent/'Textures'
im=np.array(Image.open(P/'Blade_Engraving_Source.png').convert('L'),dtype=np.float32)/255
ys,xs=np.where(im>.16)
x0,x1=max(0,xs.min()-15),min(im.shape[1],xs.max()+16)
y0,y1=max(0,ys.min()-15),min(im.shape[0],ys.max()+16)
im=im[y0:y1,x0:x1]
W,H=1024,4096
v,u=np.mgrid[0:H,0:W].astype(np.float32);u/=W-1;v/=H-1
mask=map_coordinates(im,[(v-.025)/.95*(im.shape[0]-1),(u-.20)/.60*(im.shape[1]-1)],order=1,mode='constant',cval=0)
mask=np.clip((mask-.015)/.9,0,1)
rng=np.random.default_rng(100406)
noise=rng.normal(0,1,(H,W)).astype(np.float32)
grain=gaussian_filter(noise,(.3,1.6))
damascene=np.sin(u*96+np.sin(v*100)*.7+np.sin(v*34)*1.1)*.5+.5
edge=np.clip((np.abs(u-.5)-.315)/.095,0,1)
tone=83+3*grain+5*damascene+67*edge
rgb=np.stack([tone*.97,tone,tone*1.035],axis=-1)
rgb=rgb*(1-mask[...,None])+(np.array([178,184,187])*mask[...,None])
rough=.39+.025*grain+.016*damascene-.09*edge-.10*mask
height=-gaussian_filter(mask,.65)*.000035+grain*.0000006
dv,du=np.gradient(height,1.11/(H-1),.11/(W-1))
normal=np.stack([-du,dv,np.ones_like(du)],axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
orm=np.stack([np.ones_like(mask)-mask*.02,np.clip(rough,.22,.6),np.ones_like(mask)*.98],axis=-1)
for name,array in [('BaseColor',rgb/255),('ORM',orm),('Normal',normal*.5+.5)]:
    Image.fromarray(np.uint8(np.clip(array,0,1)*255),'RGB').save(P/('Blade_'+name+'.png'))
Image.fromarray(np.uint8(mask*255),'L').save(P/'Blade_Engraving_Mask.png')
print('XUANCHI_BLADE_MAPS_SAVED 1024x4096')
