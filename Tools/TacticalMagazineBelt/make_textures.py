"""Original textile, pad, polymer and coated-metal fields for the game asset."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

R=Path(__file__).resolve().parents[2]/'SourceAssets/TacticalMagazineBelt20261024';T=R/'Textures';T.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(2026102407)
def png(p,a):Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5)).save(p)
def field(name,color,rough,metal,kind,n=2048):
    y,x=np.mgrid[:n,:n].astype('f')/n;span=.04
    noise=gaussian_filter(rng.normal(size=(n,n)).astype('f'),1.2,mode='wrap');noise/=noise.std()
    cloud=gaussian_filter(noise,22,mode='wrap');cloud/=cloud.std()
    wx=np.cos(2*np.pi*88*x);wy=np.cos(2*np.pi*88*y)
    if kind=='pad':
        a=np.cos(2*np.pi*12*x);b=np.cos(2*np.pi*12*y)
        h=.00014*(.5*(a+b)-.3*(a*b))+.000013*noise
        var=.045*(a+b)+.018*cloud
    elif kind=='webbing':
        h=.000032*(.85*wx+.25*wy+.12*noise);var=.045*wx+.02*wy+.02*cloud
    elif kind=='nylon':
        checker=np.cos(np.pi*(np.floor(x*88)+np.floor(y*88)))
        h=.000029*(.45*(wx+wy)+.26*checker*(wx-wy)+.1*noise);var=.025*(wx+wy)+.02*cloud
    elif kind=='metal':
        brush=gaussian_filter(noise,(.5,18),mode='wrap');brush/=brush.std()
        h=.000003*brush+.000002*noise;var=.028*brush+.014*cloud
    else:
        h=.000009*noise+.000004*cloud;var=.025*noise+.016*cloud
    h=gaussian_filter(h,.55,mode='wrap')
    dx=(np.roll(h,-1,1)-np.roll(h,1,1))/(2*span/n);dy=(np.roll(h,-1,0)-np.roll(h,1,0))/(2*span/n)
    normal=np.stack((-dx,dy,np.ones_like(dx)),axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    png(T/f'T_{name}_BaseColor.png',np.array(color)[None,None,:]*(1+var[...,None]))
    png(T/f'T_{name}_Normal.png',normal*.5+.5)
    png(T/f'T_{name}_ORM.png',np.stack((np.clip(1-.02*np.maximum(-noise,0),.92,1),np.clip(rough+.024*noise+.018*cloud,.24,.95),np.full_like(x,metal)),axis=-1))
    limit=float(np.max(np.abs(h)));Image.fromarray(np.uint16(np.clip(h/(2*limit)+.5,0,1)*65535)).save(T/f'T_{name}_Height.png')
    np.savez_compressed(T/f'HIGH_{name}.npz',height_m=h,span_m=span)
    return dict(name=name,resolution=n,tile_m=span,height_range_m=[-limit,limit],normal_convention='OpenGL',kind=kind)
rows=[field('Belt_CharcoalNylon',[.15,.16,.17],.82,0,'nylon'),field('Belt_BlackWebbing',[.09,.10,.11],.77,0,'webbing'),
      field('Belt_OliveWebbing',[.25,.26,.22],.8,0,'webbing'),field('Belt_SpacerMesh',[.085,.092,.10],.9,0,'pad'),
      field('Belt_GraphiteShell',[.12,.13,.145],.54,0,'polymer'),field('Belt_Gunmetal',[.24,.265,.29],.4,.9,'metal'),
      field('Belt_Elastic',[.065,.071,.08],.83,0,'webbing',1024),field('Magazine_Graphite',[.16,.17,.18],.56,0,'polymer'),
      field('Magazine_CoatedMetal',[.13,.15,.17],.38,.92,'metal')]
(R/'textures.json').write_text(json.dumps(dict(completed=True,maps=rows,physical_sources=True,ue_flip_normal_green=True),indent=2)+'\n',encoding='utf-8')
print('BELT_SURFACES_SAVED',len(rows)*4,flush=True)
