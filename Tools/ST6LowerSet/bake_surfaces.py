"""Author material height fields and matched normal/roughness textures in centimetres."""
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image
R=Path('D:/FPS3D/FPSGAME/SourceAssets/ST6LowerSet20261018');T=R/'Textures';T.mkdir(exist_ok=True)
n=1024;span=6.25;rng=np.random.default_rng(61018);y,x=np.mgrid[:n,:n]/n
noise=gaussian_filter(rng.normal(size=(n,n)),1.2,mode='wrap');noise/=max(noise.std(),1e-9)
coarse=gaussian_filter(rng.normal(size=(n,n)),12,mode='wrap');coarse/=coarse.std()
warp=np.sin(2*np.pi*x*112);weft=np.sin(2*np.pi*y*112)
twill=np.sin(2*np.pi*(x*56-y*112))
grid=(np.exp(-((np.sin(np.pi*x*8))/.12)**2)+np.exp(-((np.sin(np.pi*y*8))/.12)**2))
fields={
 'Fabric':(.0019*(warp+weft)+.001*twill+.0016*grid+.00045*noise,np.array([76,77,72]),.81,0.),
 'Khaki':(.0022*noise+.0012*coarse,np.array([114,103,78]),.73,0.),
 'Rubber':(.0012*noise+.0006*coarse,np.array([33,35,33]),.63,0.),
 'Stretch':(.0020*warp+.0014*weft+.0005*noise,np.array([37,39,36]),.86,0.),
}
for name,(h,color,rough,metal) in fields.items():
    dx=(np.roll(h,-1,axis=1)-np.roll(h,1,axis=1))/(2*span/n);dy=(np.roll(h,-1,axis=0)-np.roll(h,1,axis=0))/(2*span/n)
    normal=np.stack([-dx,dy,np.ones_like(h)],-1);normal/=np.linalg.norm(normal,axis=2,keepdims=True)
    rgb=np.clip(color[None,None,:]*(1+(.025*noise+.023*coarse)[...,None]),0,255).astype('uint8')
    orm=np.stack([np.clip(.96+.014*noise,.85,1),np.clip(rough+.022*noise,.3,.95),np.full_like(h,metal)],-1)
    for channel,data in [('BaseColor',rgb),('Normal',np.clip((normal*.5+.5)*255,0,255).astype('uint8')),('ORM',(orm*255).astype('uint8'))]:Image.fromarray(data).save(T/f'T_ST6_{name}_{channel}.png')
    np.savez_compressed(R/f'HIGH_{name}.npz',height_cm=h.astype('float32'),span_cm=span)
print('ST6_PBR_FIELDS_BAKED',len(fields),flush=True)
