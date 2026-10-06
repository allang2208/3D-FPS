"""Offline periodic forged-steel height-field bake, shared by Blender and UE.

The plate macro shape, edge rolls and rivets live in the game geometry. This
6.25 cm periodic field only supplies fine hammering and brushed surface detail.
"""
import json
import argparse
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

P=Path('D:/FPS3D/FPSGAME')
args=argparse.ArgumentParser()
args.add_argument('--root',default=str(P/'SourceAssets/ChainmailPants20261004'))
args.add_argument('--roughness',type=float,default=.405)
settings=args.parse_args();R=Path(settings.root)
T=R/'Textures';T.mkdir(parents=True,exist_ok=True)
size=1024;span_cm=6.25;rng=np.random.default_rng(20261004)

def field(sigma):
    a=gaussian_filter(rng.standard_normal((size,size)),sigma,mode='wrap')
    return a/max(a.std(),1e-8)

broad=field(30);hammer=field(8);brush=field((20,.6));fine=field(.8)
height=.0016*hammer+.00018*brush+.00010*fine
du=(np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))/(2*span_cm/size)
dv=(np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))/(2*span_cm/size)
normal=np.stack([-du,dv,np.ones_like(height)],axis=-1)
normal/=np.linalg.norm(normal,axis=2,keepdims=True)
base=np.array([.30,.325,.35])[None,None,:]*(1+.035*broad[:,:,None])
srgb=np.where(base<=.0031308,12.92*base,1.055*np.maximum(base,0)**(1/2.4)-.055)
rough=np.clip(settings.roughness+.017*brush+.016*broad,.29,.59)
orm=np.stack([np.clip(1-.015*np.maximum(-hammer,0),.93,1),rough,np.ones_like(height)],axis=-1)

for channel,data in [('BaseColor',srgb),('Normal',normal*.5+.5),('ORM',orm)]:
    Image.fromarray(np.round(np.clip(data,0,1)*255).astype('uint8')).save(T/('T_ChainmailPants_Steel_'+channel+'.png'))
np.savez_compressed(R/'SteelHighField.npz',height_cm=height,span_cm=span_cm)
(R/'steel_bake.json').write_text(json.dumps(dict(resolution=size,span_cm=span_cm,
    height_units='cm',normal_convention='OpenGL; flip green on Unreal import',
    source='periodic displaced steel authoring height field',maps=['BaseColor','Normal','ORM'],
    orm='R occlusion, G roughness, B metallic',runtime_height_displacement=False),indent=2))
print('STEEL_SURFACE_BAKED',size,flush=True)
