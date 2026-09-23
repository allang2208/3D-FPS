"""Original physically scaled paint, oxide and pitting maps, no image sources."""
import json
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored/Textures';OUT.mkdir(parents=True,exist_ok=True)
N=2048;R=np.random.default_rng(922103)
def field(sigma):
    a=gaussian_filter(R.random((N,N)).astype('float32'),sigma,mode='wrap')
    return np.clip((a-a.mean())/(a.std()*5)+.5,0,1)
macro=field(65);islands=field(13);grit=field(1.1);fine=R.random((N,N)).astype('float32')
chips=np.clip((islands*.70+grit*.30-.70)*13,0,1)
oxide=np.clip((macro*.50+islands*.38+grit*.12-.39)*5,0,1)
height=.11*grit+.055*fine-.40*chips-.10*np.maximum(grit-.69,0)
dx=(np.roll(height,-1,1)-np.roll(height,1,1))*.65
dy=(np.roll(height,-1,0)-np.roll(height,1,0))*.65
normal=np.stack((-dx,-dy,np.ones_like(dx)),axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
paint=np.array([.29,.315,.235])[None,None,:]*(.87+.18*macro+.09*grit)[...,None]
rust=np.array([.24,.117,.053])[None,None,:]*(.60+.75*islands+.19*grit)[...,None]
steel=np.array([.19,.20,.193])[None,None,:]*(.83+.25*grit)[...,None]
paint=paint*(1-chips[...,None])+steel*chips[...,None]
arrays={'BaseColor':paint,'RustColor':rust,'AgeMask':oxide,
        'Roughness':np.clip(.60+.14*macro+.08*grit-.16*chips,0,1),
        'Metallic':chips*.77,'Normal':normal*.5+.5}
channels={}
for key,value in arrays.items():
    path=OUT/('ServicePaint_'+key+'.png')
    Image.fromarray(np.uint8(np.clip(value,0,1)*255)).save(path);channels[key]=str(path)
(ROOT/'Authored/material-manifest.json').write_text(json.dumps(dict(channels=channels,
    source='Original deterministic procedural mineral/pigment fields, authored in this project',
    tile_size_m=.8,resolution=N),indent=2),encoding='utf-8')
print('SERVICE_PAINT_MAPS_AUTHORED')
