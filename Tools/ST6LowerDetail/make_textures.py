"""Produce metric material height fields and consistent PBR maps for ST6 lower gear."""
import json
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image
R=Path('D:/FPS3D/FPSGAME/SourceAssets/ST6LowerDetail20261024');T=R/'Textures';T.mkdir(parents=True,exist_ok=True)
rows=[]
for index,(name,n,color,rough,metal) in enumerate([
 ('Fabric',2048,[76,77,72],.81,0),('Khaki',2048,[114,103,78],.67,0),('Rubber',1024,[33,35,33],.66,0),
 ('Stretch',1024,[37,39,36],.84,0),('Gunmetal',1024,[64,70,73],.43,.95),('Thread',512,[97,89,71],.85,0)]):
    rng=np.random.default_rng(610240+index);y,x=np.mgrid[:n,:n]/n
    def noise(s):
        a=gaussian_filter(rng.normal(size=(n,n)),s,mode='wrap');return a/max(a.std(),1e-8)
    grain=noise(.8);coarse=noise(n/90);cloud=noise(n/18)
    if name=='Fabric':
        warp=np.sin(2*np.pi*x*112);weft=np.sin(2*np.pi*y*112)
        twill=np.sin(2*np.pi*(x*56-y*112));grid=np.exp(-(np.sin(np.pi*x*8)/.12)**2)+np.exp(-(np.sin(np.pi*y*8)/.12)**2)
        h=.0016*(warp+weft)+.001*twill+.0021*grid+.00028*grain
        variation=.019*coarse+.008*cloud+.009*(warp+weft)+.014*grid
    elif name=='Khaki':
        pores=np.maximum(-coarse-.2,0)**1.4
        h=.0025*coarse-.0012*pores+.00045*grain+.00045*cloud
        variation=.021*coarse+.012*cloud-.012*pores
    elif name=='Stretch':
        rib=np.sin(2*np.pi*x*88)+.6*np.sin(2*np.pi*y*144+.4*np.sin(2*np.pi*x*88))
        h=.0017*rib+.00035*grain;variation=.018*rib+.014*coarse
    elif name=='Rubber':
        h=.0008*grain+.0009*coarse+.0002*np.sin(2*np.pi*x*170)
        variation=.012*coarse+.007*cloud
    elif name=='Gunmetal':
        brush=noise((.7,16));h=.00038*brush+.00012*grain
        variation=.024*brush+.018*cloud
    else:
        twist=np.sin(2*np.pi*(x*130+y*18));h=.0012*twist+.0002*grain;variation=.025*twist+.01*coarse
    span=6.25;dx=(np.roll(h,-1,1)-np.roll(h,1,1))/(2*span/n);dy=(np.roll(h,-1,0)-np.roll(h,1,0))/(2*span/n)
    normal=np.stack([-dx,dy,np.ones_like(h)],-1);normal/=np.linalg.norm(normal,axis=2,keepdims=True)
    rgb=np.clip(np.array(color)[None,None,:]*(1+variation[...,None]),0,255).astype('uint8')
    orm=np.stack([np.clip(.975+.008*coarse,.9,1),np.clip(rough+.018*coarse+.009*cloud,.25,.96),np.full_like(h,metal)],-1)
    for channel,data in [('BaseColor',rgb),('Normal',((normal*.5+.5)*255).clip(0,255).astype('uint8')),('ORM',(orm*255).astype('uint8'))]:Image.fromarray(data).save(T/f'T_ST6_{name}_{channel}.png')
    normalized=(h-h.min())/max(float(np.ptp(h)),1e-8);Image.fromarray((normalized*65535).astype('uint16')).save(T/f'T_ST6_{name}_Height.png')
    np.savez_compressed(R/f'HIGH_{name}.npz',height_cm=h.astype('float32'),span_cm=span)
    rows.append(dict(name=name,resolution=n,span_cm=span,height_range_cm=[float(h.min()),float(h.max())],normal_convention='OpenGL',cloth=name in ('Fabric','Stretch','Thread')))
(R/'textures.json').write_text(json.dumps(dict(maps=rows,source='original metric surface fields; shared BaseColor/Normal/ORM masks'),indent=2),encoding='utf-8')
print('ST6_DETAIL_TEXTURES_AUTHORED',len(rows)*4,flush=True)
