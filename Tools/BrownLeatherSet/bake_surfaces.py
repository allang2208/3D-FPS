"""Matching warm leather PBR from an authored periodic micro-height field."""
import json
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.spatial import cKDTree
from PIL import Image
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BrownLeatherSet20261004';T=R/'Textures';T.mkdir(exist_ok=True)
reference=json.loads((P/'SourceAssets/GloveCompanionDetail20260928/Fingerless/artwork.json').read_text())
color=np.array(reference['mean_linear']);n=1024;span=6.25;rng=np.random.default_rng(20261004)
def noise(sigma):
    v=gaussian_filter(rng.standard_normal((n,n)),sigma,mode='wrap');return v/max(v.std(),1e-8)
yy,xx=np.mgrid[:n,:n];cells=rng.random((4100,2))*n
dist,_=cKDTree(cells,boxsize=n).query(np.c_[xx.ravel(),yy.ravel()],k=2)
edge=(dist[:,1]-dist[:,0]).reshape(n,n);grain=1-np.exp(-edge/1.40)
broad=noise(34);fine=noise(.8);h=.00145*grain+.00018*noise(7)+.000065*fine
step=span/n;du=(np.roll(h,-1,1)-np.roll(h,1,1))/(2*step);dv=(np.roll(h,-1,0)-np.roll(h,1,0))/(2*step)
normal=np.stack([-du,dv,np.ones_like(h)],-1);normal/=np.linalg.norm(normal,axis=2,keepdims=True)
base=color[None,None,:]*(.94+.10*grain[...,None]+.06*broad[...,None])
base=np.maximum(base,0);srgb=np.where(base<=.0031308,base*12.92,1.055*base**(1/2.4)-.055)
orm=np.stack([.94+.06*grain,np.clip(.68+.030*broad-.035*grain,.55,.79),np.zeros_like(grain)],-1)
for channel,data in [('BaseColor',srgb),('Normal',normal*.5+.5),('ORM',orm)]:
    Image.fromarray(np.round(np.clip(data,0,1)*255).astype('uint8')).save(T/('T_BrownLeather_'+channel+'.png'))
np.savez_compressed(R/'LeatherHighField.npz',height_cm=h,span_cm=span)
(R/'surface_bake.json').write_text(json.dumps(dict(resolution=n,span_cm=span,reference_glove='ue_field_gloves',
    reference_linear_color=color.tolist(),source='new periodic leather grain field; color family from existing fingerless glove production record',
    normal='OpenGL, flip green on UE import',orm='R occlusion, G roughness, B metallic',POM=False),indent=2))
print('BROWN_LEATHER_SURFACE_BAKED',flush=True)
