"""Author physically scaled forged-metal microrelief and contained lightning maps."""
from pathlib import Path
import json, numpy as np
from PIL import Image, ImageDraw, ImageFilter
P=Path(__file__).resolve().parent;T=P/'Textures';T.mkdir(exist_ok=True)
N=2048;rng=np.random.default_rng(31030)
y,x=np.mgrid[0:N,0:N].astype(np.float32);u=x/N;v=y/N
grain=rng.normal(0,1,(N,N)).astype(np.float32)
coarse=np.asarray(Image.fromarray(np.uint8(rng.uniform(0,255,(128,128)))).resize((N,N),Image.Resampling.BICUBIC),np.float32)/255-.5
height=.018*coarse+.0015*grain+.003*np.sin(u*2*np.pi*280+coarse*8)
gy,gx=np.gradient(height);normal=np.stack((-gx*.8,gy*.8,np.ones_like(x)),2);normal/=np.linalg.norm(normal,axis=2)[:,:,None]
def save(name,a):Image.fromarray(np.uint8(np.clip(a,0,1)*255)).save(T/('T_ZhenTing_'+name+'.png'))
save('MetalNormal',normal*.5+.5)
shade=np.clip(.40+.015*coarse+.001*grain,.1,.8)
save('MetalBaseColor',np.stack((shade*.91,shade*.95,shade),2))
save('MetalORM',np.stack((np.clip(.92+coarse*.12,0,1),np.clip(.44+coarse*.05+grain*.003,.22,.7),np.ones_like(x)*.96),2))
# Thin real geometry carries these blue-white groove maps, never a large glass window.
M=1024;yy,xx=np.mgrid[0:M,0:M].astype(np.float32)
filament=.82+.18*np.sin(xx*.025+np.sin(yy*.017))**2
save('CoreEmission',np.stack((filament*.38,filament*.76,filament),2))
save('CoreBaseColor',np.stack((filament*.025,filament*.06,filament*.11),2))
(P/'texture_manifest.json').write_text(json.dumps({'resolution_metal':N,'resolution_core':M,'normal_convention':'OpenGL; UE flip_green_channel=true','source':'authored seeded microrelief; structural chevrons, braids, panel reveals and seams are real geometry','complete':True},indent=2),encoding='utf-8')
print('ZHENTING_PBR_MAPS_AUTHORED')
