"""Author original tileable grayscale PBR surfaces; OpenGL normal convention."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
P=Path(__file__).resolve().parent/'Textures';P.mkdir(exist_ok=True)
N=2048
y,x=np.mgrid[0:N,0:N].astype(np.float32)/N
rng=np.random.default_rng(927)
grain=rng.normal(0,1,(N,N)).astype(np.float32)
def srgb(c):return np.where(c<=.0031308,c*12.92,1.055*np.maximum(c,0)**(1/2.4)-.055)
def write(key,base,rough,height):
 Image.fromarray(np.uint8(np.repeat(np.clip(srgb(base),0,1)[:,:,None],3,2)*255)).save(P/(key+'_BaseColor.png'))
 Image.fromarray(np.uint8(np.clip(rough,0,1)*255)).save(P/(key+'_Roughness.png'))
 # Both axes cover 10 cm. v increases upward while PNG row increases downward.
 dx=(np.roll(height,-1,1)-np.roll(height,1,1))*N/.2
 dy=(np.roll(height,1,0)-np.roll(height,-1,0))*N/.2
 normal=np.stack((-dx,-dy,np.ones_like(dx)),axis=2)
 normal/=np.linalg.norm(normal,axis=2)[:,:,None]
 Image.fromarray(np.uint8(np.clip(normal*.5+.5,0,1)*255)).save(P/(key+'_Normal.png'))
stripe=np.where((np.floor(x*16).astype(int)%2)==0,1,-1)
herringbone=.5+.5*np.cos(2*np.pi*(y*64+stripe*x*48))
height=.000045*herringbone+.000005*grain
write('Leather',np.clip(.055+.024*herringbone+.002*grain,.03,.10),.67-.07*herringbone+.015*grain,height)
warp=.5+.5*np.cos(2*np.pi*x*240)
weft=.5+.5*np.cos(2*np.pi*y*240)
over=(np.floor(x*120).astype(int)+np.floor(y*120).astype(int))%2
fiber=warp*(.65+.35*over)+weft*(1-.35*over)
write('Textile',np.clip(.19+.045*fiber+.003*grain,.15,.30),.78-.06*fiber+.01*grain,.000020*fiber+.000003*grain)
brushed=.5+.5*np.cos(2*np.pi*y*470+.15*np.sin(2*np.pi*x*8))
write('Steel',np.clip(.47+.015*brushed+.001*grain,.44,.50),.32+.065*brushed+.004*grain,.0000015*brushed)
(P/'provenance.json').write_text(json.dumps({'authoring':'Original procedural herringbone leather, woven fiber and satin steel','resolution':[N,N],'normal':'OpenGL; flip green once at UE texture import','color':'linear authoring encoded to sRGB once','metallic':{'Leather':0,'Textile':0,'Steel':.9}},indent=2),encoding='utf-8')
print('GRIP_PBR_WRITTEN',flush=True)
