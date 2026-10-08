"""Original tileable woven cotton surface maps for the modeled robe remnants."""
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006/Textures')
rng=np.random.default_rng(10626);n=2048
y,x=np.mgrid[0:n,0:n].astype(np.float32);x/=n;y/=n
stain=gaussian_filter(rng.random((n,n),dtype=np.float32),45,mode='wrap');stain=(stain-stain.mean())/max(float(stain.std()),1e-6)
fibers=gaussian_filter(rng.random((n,n),dtype=np.float32),(.5,8),mode='wrap')
warp=np.cos(x*np.pi*2*160);weft=np.cos(y*np.pi*2*160)
over=np.sin(x*np.pi*2*80)*np.sin(y*np.pi*2*80)
height=(warp+weft)*.12+over*.18+fibers*.08
dy,dx=np.gradient(height);normal=np.stack((-dx*2.0,-dy*2.0,np.ones_like(dx)),axis=2);normal/=np.linalg.norm(normal,axis=2)[:,:,None]
base=np.array([86,91,65],dtype=np.float32)[None,None,:]*(.95+stain[:,:,None]*.075+height[:,:,None]*.12)
rough=np.clip(.86+stain*.025+height*.035,.69,.97)
Image.fromarray(np.uint8(np.clip(base,0,255))).save(ROOT/'BC_Fabric_BaseColor.png')
Image.fromarray(np.uint8(np.clip(normal*.5+.5,0,1)*255)).save(ROOT/'BC_Fabric_Normal.png')
Image.fromarray(np.uint8(rough*255)).save(ROOT/'BC_Fabric_Roughness.png')
