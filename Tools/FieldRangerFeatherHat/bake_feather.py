"""Bake physical vane ridges and restrained feather pigmentation; opaque geometry."""
import json,math
from pathlib import Path
import numpy as np
from PIL import Image
R=Path('D:/FPS3D/FPSGAME/SourceAssets/FieldRangerFeatherHat20261021');T=R/'Textures';T.mkdir(exist_ok=True)
ny,nx=2048,1024
v,u=np.mgrid[:ny,:nx].astype('float32');u/=nx;v/=ny
x=(u-.5)*2
barb=np.cos(math.tau*(v*155-abs(x)*9))
fiber=np.cos(math.tau*(v*615-abs(x)*36))
h=.003*(.5+.5*barb)**3+.00045*fiber+.009*np.exp(-(x/.025)**2)
dy,dx=np.gradient(h,19./ny,5./nx)
n=np.stack((-dx,-dy,np.ones_like(h)),-1);n/=np.linalg.norm(n,axis=-1,keepdims=True)
tip=np.clip((v-.65)/.28,0,1);tip=tip*tip*(3-2*tip)
base=np.array([.60,.54,.43]);dark=np.array([.22,.16,.11])
color=base*(1-tip[...,None])+dark*tip[...,None]
color*=1+.055*barb[...,None]+.025*fiber[...,None]
color*=1-.11*np.exp(-(x/.055)**2)[...,None]
rough=np.clip(.73+.05*barb-.08*np.exp(-(x/.035)**2),.48,.85)
for name,data in [('BaseColor',color),('Normal',n*.5+.5),('ORM',np.stack((np.clip(1-(h.max()-h)*10,.85,1),rough,np.zeros_like(h)),-1))]:
 Image.fromarray(np.uint8(np.clip(data,0,1)*255+.5)).save(T/('Feather_'+name+'.png'))
np.save(T/'Feather_height_cm.npy',h)
(R/'surface_source.json').write_text(json.dumps(dict(completed=True,feather_maps=[1024,2048],physical_span_cm=[5,19],normal='OpenGL; UE flips green',cloth_leather='Shared FieldRangerTop20261020 8cm PBR',runtime_tested=False),indent=2),encoding='utf-8')
print('RANGER_FEATHER_SURFACES_BAKED',flush=True)
