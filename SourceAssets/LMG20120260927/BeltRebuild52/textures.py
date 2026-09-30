"""Subtle metal grain only; no inherited pouch/fabric atlas or cloth normal."""
from pathlib import Path
import numpy as np
from PIL import Image
O=Path(__file__).parent/'Textures';O.mkdir(exist_ok=True)
n=512;rng=np.random.default_rng(2052)
grain=rng.normal(0,.10,(n,n));rings=np.repeat(rng.normal(0,.055,(n,1)),n,axis=1)
field=np.clip(.5+grain+rings,.06,.94)
Image.fromarray(np.repeat(np.uint8(field[:,:,None]*255),3,axis=2)).save(O/'T_B52_MetalFinish.png')
# A very small surface slope: retain clean hard-surface silhouette and reflections.
dx=(np.roll(field,-1,1)-np.roll(field,1,1))*.03;dy=(np.roll(field,-1,0)-np.roll(field,1,0))*.03
normal=np.stack([-dx,dy,np.ones_like(dx)],2);normal/=np.linalg.norm(normal,axis=2,keepdims=True)
Image.fromarray(np.uint8(np.clip(normal*.5+.5,0,1)*255)).save(O/'T_B52_MicroNormal.png')
