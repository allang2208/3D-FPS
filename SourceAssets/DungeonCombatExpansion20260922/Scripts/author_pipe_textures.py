"""Original seamless enamel / exposed steel / localized oxidation, 80 cm texture tile."""
import numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored/Textures';OUT.mkdir(exist_ok=True)
n=2048;r=np.random.default_rng(922317)
def noise(sigma):
    v=gaussian_filter(r.normal(size=(n,n)).astype(np.float32),sigma,mode='wrap');return v/max(float(v.std()),1e-6)
macro=noise(86);mid=noise(15);grain=noise(.65);pit=noise(2)
chips=np.clip((mid+macro*.55-1.40)*2.2,0,1);rust=np.clip((macro*.9+mid*.35-1.47)*2.3,0,1)*chips
enamel=np.array([78,97,89],np.float32);steel=np.array([102,111,109],np.float32);oxid=np.array([101,59,31],np.float32)
base=enamel[None,None,:]+macro[:,:,None]*3+grain[:,:,None]*.7
base=base*(1-chips[:,:,None])+steel*chips[:,:,None];base=base*(1-rust[:,:,None])+oxid*rust[:,:,None]
rough=np.clip(.30+mid*.014+chips*.13+rust*.31,.24,.83)
metal=chips*(1-rust)*.86
# Millimetre-scale shallow paint loss and micro pits; a steel pipe does not have stone relief.
height=grain*.000009-chips*.00012-rust*np.maximum(pit,0)*.00005
gy,gx=np.gradient(height,.8/n);normal=np.stack([-gx,-gy,np.ones_like(gx)],axis=-1);normal/=np.linalg.norm(normal,axis=-1)[:,:,None]
maps={'BaseColor':np.clip(base,0,255).astype(np.uint8),'Normal':np.clip((normal*.5+.5)*255,0,255).astype(np.uint8),'Surface':np.stack([rough,metal,rust],axis=-1)*255}
paths={}
for key,arr in maps.items():
    path=OUT/('PipeEnamel_'+key+'.png');Image.fromarray(arr.astype(np.uint8),'RGB').save(path);paths[key]=str(path)
(ROOT/'Authored/pipe-textures.json').write_text(json.dumps(paths,indent=2))
print('PIPE_PBR_AUTHORED',len(paths))
