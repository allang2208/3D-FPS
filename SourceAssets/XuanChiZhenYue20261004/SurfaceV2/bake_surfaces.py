"""Legacy V2 blade maps and current copper hilt atlas; preserve incised relief."""
import runpy
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
P=Path(__file__).resolve().parent;S=P.parent/'ModelV1/Textures';D=P/'Textures';D.mkdir(parents=True,exist_ok=True)
def save(name,a):Image.fromarray(np.uint8(np.clip(a,0,1)*255)).save(D/(name+'.png'))
mask=np.asarray(Image.open(S/'Blade_Engraving_Mask.png'),dtype=np.float32)/255
H,W=mask.shape;v,u=np.mgrid[0:H,0:W].astype(np.float32);u/=W-1;v/=H-1
ink=gaussian_filter(mask,.70);groove=np.clip(ink,0,1)**.7
grain=gaussian_filter(np.random.default_rng(1004042).normal(size=(H,W)).astype(np.float32),(.4,2.))
# 0.30 mm cut into the steel, with a narrow 0.018 mm rolled lip.
lip=np.clip(gaussian_filter(groove,2.2)-groove,0,1)
height=-groove*.00030+lip*.000018+grain*.00000065
dv,du=np.gradient(height,1.20/(H-1),.11/(W-1))
n=np.stack([-du,dv,np.ones_like(du)],axis=-1);n/=np.linalg.norm(n,axis=-1,keepdims=True)
palette=np.array([108,113,116],dtype=np.float32)/255
bc=palette[None,None,:]*(1+.015*grain[...,None]-.07*groove[...,None])
rough=.38+.012*grain+.055*groove-.02*lip
ao=1-.26*groove
orm=np.stack([ao,np.clip(rough,.29,.50),np.ones_like(ao)*.97],axis=-1)
z=(1-v)*1.2
width=np.interp(z,[0,.16,.30,.88,1.035,1.15,1.19,1.2],[.040,.040,.042,.038,.032,.019,.005,.00003])
edge=np.clip((width-np.abs((u-.5)*.11)-.003)/.005,0,1)
end=np.clip(np.minimum(v,1-v)/.018,0,1)
relief=np.stack([np.clip(1+height/.00032,0,1),np.zeros_like(ao),edge*end],axis=-1)
for name,a in [('BaseColor',bc),('Normal',n*.5+.5),('ORM',orm),('Relief',relief)]:save('Blade_'+name,a)
runpy.run_path(str(P/'bake_hilt.py'),run_name='__main__')
print('XUANCHI_SURFACE_V2_MAPS_SAVED',flush=True)
