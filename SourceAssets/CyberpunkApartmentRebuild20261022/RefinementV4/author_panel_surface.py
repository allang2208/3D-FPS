"""A physical engraved-height field supplies matched normal and roughness detail."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parent;out=ROOT/'Textures';out.mkdir(exist_ok=True)
n=2048;period=.48
y,x=np.mgrid[0:n,0:n].astype(np.float32)/n
# Restrained 40 micron laser-etched channels; this is not inferred from albedo.
diag=np.abs(np.mod((x+y)*4+.5,1)-.5)
line=np.exp(-(diag/.008)**2)
zone=(np.mod(y*4,1)>.70).astype(np.float32)
height=-.000040*line*zone
gx=(np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))/(2*period/n)
gy=(np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))/(2*period/n)
# Image rows follow UE V. Tangent-space DirectX slope; no import green flip.
normal=np.stack((-gx,-gy,np.ones_like(gx)),axis=-1)
normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
Image.fromarray(np.uint8(np.clip(normal*.5+.5,0,1)*255)).save(out/'T_AP4_Etch_N.png')
rough=np.clip(.40+.18*line*zone,0,1)
orm=np.stack((1-.12*line*zone,rough,np.ones_like(x)*.82),axis=-1)
Image.fromarray(np.uint8(orm*255)).save(out/'T_AP4_Etch_ORM.png')
Image.fromarray(np.uint16((height/.000040+1)*65535)).save(out/'T_AP4_Etch_Height.png')
(ROOT/'surface-source.json').write_text(json.dumps(dict(period_m=period,resolution=n,groove_depth_m=.000040,
 method='physical height derivative; not colour-derived, not a scan',normal='DirectX; UE V follows image rows',
 runtime_height_sampling=False,normal_and_roughness_share_height_mask=True),indent=2),encoding='utf8')
print('CABINET_SURFACE_TEXTURES_AUTHORED')
