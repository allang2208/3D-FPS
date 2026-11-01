"""Small, tileable dry-surface detail. Wetness remains on the shared UE master."""
import numpy as np
from PIL import Image
from pathlib import Path
O=Path(__file__).resolve().parent/'Textures';O.mkdir(exist_ok=True)
n=1024;y,x=np.mgrid[:n,:n]/n;rng=np.random.default_rng(24029)
def normal(name,h):
    dy,dx=np.gradient(h,.1/n);v=np.stack((-dx,-dy,np.ones_like(h)),axis=-1);v/=np.linalg.norm(v,axis=-1,keepdims=True)
    Image.fromarray(np.uint8(np.clip((v*.5+.5)*255,0,255))).save(O/(name+'.png'))
noise=rng.random((n,n))-.5
normal('T_M24_AAS_Metal_N',np.sin(y*2*np.pi*251)*.0000008+noise*.0000004)
normal('T_M24_AAS_Polymer_N',np.sin(x*2*np.pi*71)*np.sin(y*2*np.pi*73)*.000004+noise*.0000005)
Image.new('RGBA',(4,4),(0,0,255,255)).save(O/'T_M24_AAS_SurfaceMask.png')
print('M24_ADVANCED_ACTION_TEXTURES_AUTHORED')
