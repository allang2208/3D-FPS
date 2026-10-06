"""Author periodic leather and sole height fields, then bake matching PBR maps."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
from scipy.spatial import cKDTree

R=Path('D:/FPS3D/FPSGAME/SourceAssets/ArmoredBoots20261004');T=R/'Textures';T.mkdir(exist_ok=True)
rng=np.random.default_rng(20261004);n=1024;span=6.25
def noise(sigma):
    a=gaussian_filter(rng.standard_normal((n,n)),sigma,mode='wrap')
    return a/max(a.std(),1e-8)
def bake(name,h,color,rough,ao):
    step=span/n
    du=(np.roll(h,-1,1)-np.roll(h,1,1))/(2*step)
    dv=(np.roll(h,-1,0)-np.roll(h,1,0))/(2*step)
    normal=np.stack([-du,dv,np.ones_like(h)],-1);normal/=np.linalg.norm(normal,axis=2,keepdims=True)
    srgb=np.where(color<=.0031308,12.92*color,1.055*np.maximum(color,0)**(1/2.4)-.055)
    orm=np.stack([ao,rough,np.zeros_like(h)],-1)
    for key,a in [('BaseColor',srgb),('Normal',normal*.5+.5),('ORM',orm)]:
        Image.fromarray(np.round(np.clip(a,0,1)*255).astype('uint8')).save(T/f'T_ArmoredBoots_{name}_{key}.png')
    np.savez_compressed(R/f'{name}HighField.npz',height_cm=h,span_cm=span)

# Periodic leather grain cells, with depressed borders and flattened crowns.
centers=rng.random((3600,2))*n;yy,xx=np.mgrid[:n,:n]
dist,_=cKDTree(centers,boxsize=n).query(np.c_[xx.ravel(),yy.ravel()],k=2)
border=(dist[:,1]-dist[:,0]).reshape(n,n)
grain=1-np.exp(-border/1.35);broad=noise(28);fine=noise(.8)
h=.0018*grain+.00008*fine+.00025*noise(7)
color=np.array([.024,.021,.019])[None,None,:]*(.90+.12*grain[...,None]+.055*broad[...,None])
bake('Leather',h,color,np.clip(.64+.045*broad-.045*grain,.48,.79),np.clip(.92+.08*grain,.9,1))
solefield=noise((1.4,24));h=.00065*solefield+.00012*fine
color=np.array([.020,.015,.011])[None,None,:]*(1+.08*solefield[...,None])
bake('Sole',h,color,np.clip(.80+.035*broad,.70,.91),np.ones((n,n)))
(R/'surface_bake.json').write_text(json.dumps(dict(resolution=n,span_cm=span,
    authored_fields=['LeatherHighField.npz','SoleHighField.npz'],normal='OpenGL; flip green in UE',
    orm='R occlusion, G roughness, B metallic',steel='reuse ChainmailPants ArmorRefineV2 forged steel',
    geometry='plate relief, bevels, edge rolls and coarse welt seam; fine grain baked from periodic height'),indent=2))
print('ARMORED_BOOT_SURFACES_BAKED',flush=True)
