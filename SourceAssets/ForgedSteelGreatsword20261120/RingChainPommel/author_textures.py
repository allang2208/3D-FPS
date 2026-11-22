"""Seamless satin steel and oxidized iron finishes for the socket and chain."""
from pathlib import Path
import numpy as np
from PIL import Image

out = Path(__file__).resolve().parent
size = 512
rng = np.random.default_rng(37)
y,x = np.indices((size,size))
grain = rng.normal(0,1,(size,size))
band = (.65*np.cos(2*np.pi*(7*x+2*y)/size)+.35*np.sin(2*np.pi*(19*y-3*x)/size))
grind = .6*np.sin(2*np.pi*(105*y+3*x)/size)+.4*np.cos(2*np.pi*(43*y+4*x)/size)
scratch = np.zeros_like(grain)
for _ in range(198):
    cx,cy = rng.integers(0,size,2)
    length = rng.uniform(6,65)
    dx = (x-cx+size/2)%size-size/2
    dy = (y-cy+size/2)%size-size/2 - dx*rng.uniform(-.21,.21)
    scratch += np.maximum(0.,1.-abs(dx)/length)*np.maximum(0.,1.-abs(dy)/.85)
chain = x>=size//2
base = np.where(chain[...,None],[83.,78.,72.],[112.,114.,115.])
color = base+(4.2*band+2.6*grain+1.4*grind+13.*scratch)[...,None]
rough = np.where(chain,129.,100.) + 10.*band+4.*grain+6.*grind-29.*scratch
metal = np.where(chain,210.,231.)+4.*grain+8.*scratch
height = .019*grain+.009*grind-.042*scratch
normal = np.stack((-(np.roll(height,-1,axis=1)-np.roll(height,1,axis=1)),
                    np.roll(height,-1,axis=0)-np.roll(height,1,axis=0),np.ones_like(grain)),axis=-1)
normal /= np.linalg.norm(normal,axis=-1,keepdims=True)
for name,pixels in [('BaseColor',color),('ORM',np.stack((np.full_like(grain,255.),rough,metal),axis=-1)),
                    ('Normal',(normal*.5+.5)*255.)]:
    Image.fromarray(np.clip(pixels,0,255).round().astype('uint8')).save(out/('T_RingChain_'+name+'.png'))
