"""Original felt, leather and satin surface fields. Production maps, no renders."""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw
import os
from scipy.ndimage import gaussian_filter

R=Path(os.environ.get('ST6_BERET_ROOT','D:/FPS3D/FPSGAME/SourceAssets/ST6Beret20261023/SurfaceV2'));T=R/'Textures';T.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(20261023)
def png(name,a):Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5)).save(T/name)
def noise(n,sigma):
    a=gaussian_filter(rng.normal(size=(n,n)).astype('f'),sigma,mode='wrap');return a/max(float(a.std()),1e-9)
def maps(name,n,span,base,rough,kind):
    grain=noise(n,1.1);cloud=noise(n,18);fine=noise(n,.55)
    y,x=np.mgrid[:n,:n]/n
    if kind=='felt':
        strands=Image.new('F',(n,n));draw=ImageDraw.Draw(strands)
        for _ in range(12000):
            xx,yy=rng.uniform(0,n,2);angle=rng.uniform(0,np.pi);length=rng.uniform(8,48);dx=np.cos(angle)*length;dy=np.sin(angle)*length;value=float(rng.uniform(.2,1))
            for ox in (-n,0,n):
                for oy in (-n,0,n):draw.line((xx+ox,yy+oy,xx+ox+dx,yy+oy+dy),fill=value,width=1)
        strand=gaussian_filter(np.asarray(strands),.55,mode='wrap');strand=(strand-strand.mean())/max(strand.std(),1e-8)
        fibers=(gaussian_filter(rng.normal(size=(n,n)),(.6,5),mode='wrap')+gaussian_filter(rng.normal(size=(n,n)),(4,.7),mode='wrap'))
        fibers/=fibers.std();height=.000035*(.25*grain+.22*fibers+.10*fine+.43*strand)
        variation=.023*cloud+.018*grain+.012*fibers+.026*strand;roughness=np.clip(rough+.025*cloud+.018*fine-.016*strand,.70,.92)
    elif kind=='leather':
        pores=np.maximum(-grain-.65,0);height=.000028*(grain-.9*pores)+.000014*cloud
        variation=.035*cloud+.045*grain;roughness=np.clip(rough+.06*grain,.31,.64)
    elif kind=='metal':
        brush=gaussian_filter(rng.normal(size=(n,n)),(.55,24),mode='wrap');brush/=brush.std();oxide=np.maximum(cloud-.6,0)
        height=.000004*brush+.000002*grain;variation=.035*brush-.045*oxide;roughness=np.clip(rough+.035*brush+.055*oxide,.28,.58)
    else:
        warp=np.sin(2*np.pi*128*x);weft=np.sin(2*np.pi*128*y)
        height=.000012*(warp+weft)+.000005*grain
        variation=.025*warp+.02*weft+.02*cloud;roughness=np.clip(rough+.025*grain,.35,.65)
    color=np.array(base)[None,None,:]*(1+variation[:,:,None]);dx=(np.roll(height,-1,1)-np.roll(height,1,1))/(2*span/n);dy=(np.roll(height,-1,0)-np.roll(height,1,0))/(2*span/n)
    normal=np.stack([-dx,dy,np.ones_like(dx)],-1);normal/=np.linalg.norm(normal,axis=2,keepdims=True)
    png('T_'+name+'_BaseColor.png',color);png('T_'+name+'_Normal.png',normal*.5+.5)
    png('T_'+name+'_ORM.png',np.stack([np.clip(1-np.maximum(-grain,0)*.015,.90,1),roughness,np.full_like(dx,.94 if kind=='metal' else 0)],-1))
    limit=float(np.max(np.abs(height)));Image.fromarray(np.uint16(np.clip(height/(2*limit)+.5,0,1)*65535)).save(T/('T_'+name+'_Height.png'))
    return dict(name=name,resolution=n,tile_m=span,height_range_m=[-limit,limit],normal_convention='OpenGL')
rows=[maps('ST6_BurgundyFelt',2048,.06,[.34,.055,.105],.82,'felt'),maps('ST6_BlackLeather',1024,.04,[.055,.05,.048],.48,'leather'),maps('ST6_Lining',1024,.08,[.065,.041,.047],.48,'lining'),maps('ST6_DarkSilver',1024,.04,[.43,.47,.49],.39,'metal')]
(R/'textures.json').write_text(json.dumps(dict(original_procedural_sources=True,maps=rows),indent=2),encoding='utf-8')
print('ST6_BERET_PBR_MAPS_SAVED',len(rows)*4,flush=True)
