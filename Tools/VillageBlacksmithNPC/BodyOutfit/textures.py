"""Author repeating fabric, leather and hardware surfaces and a Jason-UV skin map."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

P=Path('D:/FPS3D/FPSGAME')
R=P/'SourceAssets/VillageBlacksmithNPC20261118/BodyOutfit'
O=R/'Textures'
O.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(19051)
size=1024
y,x=np.mgrid[0:size,0:size]/size
def field(sigma):
    a=gaussian_filter(rng.normal(size=(size,size)),sigma,mode='wrap')
    return a/max(a.std(),1e-8)
coarse,mid,fine=field(31),field(8),field(.8)
wear=np.clip((field(19)-.45)*.9,0,1)
def image(path,data):
    Image.fromarray(np.uint8(np.clip(data,0,255))).save(O/(path+'.png'))
for name,rgb,rough,surface in [
    ('Linen',(49,59,63),.87,'weave'),('Twill',(57,56,54),.85,'twill'),
    ('Apron',(86,58,42),.70,'hide'),('Saddle',(66,47,36),.62,'hide'),
    ('Boot',(57,43,35),.64,'hide'),('Sole',(46,40,36),.86,'rubber'),
    ('Brass',(148,109,60),.48,'metal'),('Thread',(152,125,89),.83,'weave')]:
    a=np.sin(2*np.pi*(x*128+.085*np.sin(2*np.pi*y*32)))
    b=np.sin(2*np.pi*(y*128+.055*np.sin(2*np.pi*x*32)))
    if surface in ('weave','twill'):
        twist=np.sin(2*np.pi*(x*64+(y*(64 if surface=='twill' else 0))))
        height=(a+b)*.17+a*b*twist*.24+.20*fine+.07*mid
        value=height*.115+coarse*.028+mid*.03
    elif surface=='hide':
        # Stretched creases and fine pores in a seamless field.
        ridge=np.exp(-np.abs(gaussian_filter(rng.standard_normal((size,size)),(1.8,7),mode='wrap'))*21)
        height=-ridge*.65+fine*.18+.25*mid
        value=.055*coarse+.039*mid+.029*fine-.04*ridge+.07*wear
    else:
        height=.13*fine+.06*mid
        value=.035*coarse+.035*mid+.025*fine
    color=np.array(rgb)[None,None,:]*(1+value[:,:,None])
    if surface=='hide':color+=wear[:,:,None]*np.array([10.,7.,4.])
    dx=(np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))*.54
    dy=(np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))*.54
    nor=np.stack([-dx,dy,np.ones_like(dx)],axis=-1)
    nor/=np.linalg.norm(nor,axis=-1,keepdims=True)
    masks=np.stack([np.clip(.97+.035*height,.79,1),np.clip(rough+.022*mid-.085*wear,.22,.99),np.full_like(mid,.82 if surface=='metal' else 0)],axis=-1)
    image('T_Smith_'+name+'_BC',color);image('T_Smith_'+name+'_N',(nor*.5+.5)*255);image('T_Smith_'+name+'_ORM',masks*255)
for part in ['body','head']:
    im=Image.open(P/('SourceAssets/JasonStrong20261117/R2_LongLegs/textures/T_Jason_'+part+'.png')).convert('RGB')
    # Preserve the original pore, nail, pigmentation and vein details in the UV atlas.
    a=np.asarray(im,dtype=np.float32)
    a*=np.array([.706,.622,.574],np.float32)
    image('T_Smith_Skin_'+part+'_BC',a)
