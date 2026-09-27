"""Original worked-steel PBR data; the oxide body reuses the local Normandy library."""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE=Path(__file__).parent
OUT=HERE/'Textures';OUT.mkdir(parents=True,exist_ok=True)
N=2048
rng=np.random.default_rng(269263)

def noise(n):
    tile=np.tile(rng.random((n,n),dtype=np.float32),(3,3))
    return np.array(Image.fromarray(tile).resize((N*3,N*3),Image.Resampling.BICUBIC),dtype=np.float32)[N:2*N,N:2*N]

coarse=noise(13);grain=noise(156);fine=noise(640)
peen=Image.new('L',(N,N));scratch=Image.new('L',(N,N))
p,s=ImageDraw.Draw(peen),ImageDraw.Draw(scratch)
for _ in range(2800):
    x,y=rng.integers(0,N,2);rx=int(rng.integers(2,13));ry=int(rng.integers(2,9))
    p.ellipse((int(x-rx),int(y-ry),int(x+rx),int(y+ry)),fill=int(rng.integers(15,170)))
for _ in range(980):
    x,y=rng.integers(0,N,2);angle=rng.uniform(0,np.pi);length=rng.uniform(4,90)
    s.line((int(x),int(y),int(x+np.cos(angle)*length),int(y+np.sin(angle)*length)),fill=int(rng.integers(15,160)),width=1)
peen=np.array(peen.filter(ImageFilter.GaussianBlur(1.1)),dtype=np.float32)/255
scratch=np.array(scratch.filter(ImageFilter.GaussianBlur(.45)),dtype=np.float32)/255
tarnish=np.clip((coarse-.45)*1.3,0,.38)
base=np.array([.34,.345,.342],dtype=np.float32)*(0.75+.4*grain[...,None]+.1*fine[...,None])
base=base*(1-tarnish[...,None])+np.array([.085,.069,.049])*tarnish[...,None]
base*=1-.22*peen[...,None];base+=scratch[...,None]*.025
rough=np.clip(.37+.18*grain+.17*tarnish+.1*peen-.16*scratch,.26,.72)
metal=np.clip(.99-tarnish*.6,.65,1)
height=(grain-.5)*.004+(fine-.5)*.001-peen*.009-scratch*.002
dx=(np.roll(height,-1,1)-np.roll(height,1,1))/(100/N)
dy=(np.roll(height,-1,0)-np.roll(height,1,0))/(100/N)
normal=np.stack((-dx,dy,np.ones_like(dx)),-1)
normal/=np.linalg.norm(normal,axis=-1)[...,None]
base=np.where(base<=.0031308,12.92*base,1.055*np.maximum(base,0)**(1/2.4)-.055)
for name,data in [('BaseColor',base),('ORM',np.stack((1-.18*peen,rough,metal),-1)),('Normal',normal*.5+.5)]:
    Image.fromarray(np.uint8(np.clip(data,0,1)*255+.5)).save(OUT/('T_Anvil_Worked_'+name+'.png'))
(OUT/'provenance.json').write_text(json.dumps({
    'worked_surface':'Original procedural peening, abrasion and tarnish; seed 269263',
    'body_surface':'Existing Normandy T_MetalRust_00A through BlastFurnace_WroughtIron maps; existing project asset license',
    'span_cm':50,'normal':'DirectX','reference_photos':'Visual study only; not projected or included in game textures',
    'references':['https://commons.wikimedia.org/wiki/File:Fciron-anvil_face.jpg',
                  'https://www.iforgeiron.com/topic/65975-british-military-anvil-identification/'],
    'rendered':False},indent=2),encoding='utf8')
print('ANVIL_WORKED_SURFACE_AUTHORED',flush=True)
