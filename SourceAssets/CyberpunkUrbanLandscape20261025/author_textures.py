"""Tileable numerical PBR relief for planting surfaces and missing Aspen bark normals."""
import numpy as np,json
from PIL import Image
from pathlib import Path
R=Path(__file__).resolve().parent;O=R/'Textures';O.mkdir(exist_ok=True);N=1024
rng=np.random.default_rng(251026);y,x=np.mgrid[:N,:N]/N
def smooth_noise(size):
    raw=(rng.random((size,size))*255).astype('uint8');im=Image.fromarray(np.tile(raw,(3,3)))
    a=np.asarray(im.resize((N*3,N*3),Image.Resampling.BICUBIC),dtype='float32')/255
    return a[N:2*N,N:2*N]
def normal(h,gain):
    dx=(np.roll(h,-1,1)-np.roll(h,1,1))*gain;dy=(np.roll(h,-1,0)-np.roll(h,1,0))*gain
    n=np.stack([-dx,dy,np.ones_like(dx)],-1);n/=np.linalg.norm(n,axis=-1,keepdims=True);return n*.5+.5
def save(name,a):Image.fromarray(np.uint8(np.clip(a,0,1)*255)).save(O/(name+'.png'))
fine=smooth_noise(220);mid=smooth_noise(45);broad=smooth_noise(7)
for role,base in [('Lawn',[.19,.24,.10]),('Soil',[.22,.15,.085])]:
    h=.40*fine+.35*mid+.25*broad
    if role=='Lawn':h+=.11*np.sin(2*np.pi*(x*95+y*31+mid*.3))
    color=np.array(base)[None,None,:]*(.6+.9*h[...,None]);save('T_UL_'+role+'_BC',color)
    save('T_UL_'+role+'_N',normal(h,3.2));save('T_UL_'+role+'_ORM',np.stack([.8+.18*h,.82+.15*mid,np.zeros_like(h)],-1))
bark=.44*np.sin(2*np.pi*(x*23+.13*np.sin(2*np.pi*y*3)+.07*mid))+.16*np.sin(2*np.pi*x*69)+.12*fine
save('T_UL_AspenBark_N',normal(bark,4.8))
(R/'textures.json').write_text(json.dumps(dict(stage='texture_sources_authored',files=[str(p) for p in O.glob('*.png')],resolution=N,tests_run=False),indent=2),encoding='utf8')
print('URBAN_TEXTURES_AUTHORED',len(list(O.glob('*.png'))))
