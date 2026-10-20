"""Original subtle coating microtexture; no borrowed HK texture or markings."""
import numpy as np
from PIL import Image
from pathlib import Path
from scipy.ndimage import gaussian_filter
O=Path(__file__).parent;N=1024;rng=np.random.default_rng(619)
h=gaussian_filter(rng.standard_normal((N,N)),1.1,mode='wrap')
h/=h.std()
dx=(np.roll(h,-1,1)-np.roll(h,1,1))*.006
dy=(np.roll(h,-1,0)-np.roll(h,1,0))*.006
rough=gaussian_filter(rng.standard_normal((N,N)),3.0,mode='wrap');rough/=rough.std()
arr=np.stack([.5+dx,.5+dy,np.clip(.5+rough*.10,.15,.85),np.ones_like(h)],axis=-1)
Image.fromarray(np.uint8(np.clip(arr,0,1)*255),'RGBA').save(O/'T_SVCH_SightCoating.png')
