"""Small tileable tangent normals for the weapon's own surface instances."""
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image
O=Path(__file__).parent/'Textures';O.mkdir(exist_ok=True)
rng=np.random.default_rng(20261018)
for name,amplitude,sigma in [('Metal',.012,1.1),('Polymer',.045,1.7),('Rubber',.04,2.2)]:
    height=gaussian_filter(rng.standard_normal((1024,1024)),sigma,mode='wrap')
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))/2
    dy=(np.roll(height,-1,0)-np.roll(height,1,0))/2
    scale=amplitude/max(np.std(dx),1e-9)
    normal=np.stack((-dx*scale,dy*scale,np.ones_like(height)),axis=-1)
    normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    Image.fromarray(np.uint8(np.clip((normal*.5+.5)*255,0,255)),'RGB').save(O/('T_SVCH_'+name+'_N.png'))
print('SVCH_SURFACE_TEXTURES_SAVED')
