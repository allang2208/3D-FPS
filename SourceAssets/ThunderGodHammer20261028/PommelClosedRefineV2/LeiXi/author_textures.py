"""Author physically scaled forged-metal microrelief and contained lightning maps."""
from pathlib import Path
import json, numpy as np
from PIL import Image, ImageDraw, ImageFilter
P=Path(__file__).resolve().parent;T=P/'Textures';T.mkdir(exist_ok=True)
N=4096;rng=np.random.default_rng(31030)
y,x=np.mgrid[0:N,0:N].astype(np.float32);u=x/N;v=y/N
grain=rng.normal(0,1,(N,N)).astype(np.float32)
coarse=np.asarray(Image.fromarray(np.uint8(rng.uniform(0,255,(128,128)))).resize((N,N),Image.Resampling.BICUBIC),np.float32)/255-.5
height=.018*coarse+.0015*grain+.003*np.sin(u*2*np.pi*280+coarse*8)
height=np.asarray(Image.fromarray(np.uint8(np.clip(height*10+.5,0,1)*255)).filter(ImageFilter.GaussianBlur(1.2)),np.float32)/2550
gy,gx=np.gradient(height);normal=np.stack((-gx*.8,gy*.8,np.ones_like(x)),2);normal/=np.linalg.norm(normal,axis=2)[:,:,None]
def save(name,a):Image.fromarray(np.uint8(np.clip(a,0,1)*255)).save(T/('T_LeiXi_'+name+'.png'))
save('MetalNormal',normal*.5+.5)
linear=np.clip(.40+.012*coarse+.001*grain,.1,.8)
shade=1.055*np.power(linear,1/2.4)-.055
save('MetalBaseColor',np.stack((shade*.91,shade*.95,shade),2))
save('MetalORM',np.stack((np.clip(.92+coarse*.12,0,1),np.clip(.44+coarse*.05+grain*.003,.22,.7),np.ones_like(x)*.96),2))
# Diamond UV has a physical glass aperture. Lightning remains under its metal rim.
M=1024;bolt=Image.new('L',(M,M));d=ImageDraw.Draw(bolt)
points=[(512,80),(490,230),(550,340),(440,470),(565,590),(502,755),(520,940)]
d.line(points,fill=255,width=5,joint='curve')
for pts in [[(550,340),(650,420),(620,510),(734,580)],[(440,470),(350,520),(380,624),(300,680)],[(502,755),(628,730),(670,775)],[(490,230),(390,295),(430,350)]]:d.line(pts,fill=190,width=3,joint='curve')
thin=np.asarray(bolt,np.float32)/255;glow=np.asarray(bolt.filter(ImageFilter.GaussianBlur(18)),np.float32)/255
yy,xx=np.mgrid[0:M,0:M].astype(np.float32);noise=rng.uniform(0,1,(M,M)).astype(np.float32)
core=np.clip(thin+glow*2.6+noise*.008,0,1)
save('CoreEmission',np.stack((core*.22,core*.65,core),2))
corecolor=np.stack((.014+glow*.06,.025+glow*.12,.045+glow*.20),2)
save('CoreBaseColor',corecolor)
(P/'texture_manifest.json').write_text(json.dumps({'resolution_metal':N,'resolution_core':M,'normal_convention':'OpenGL; UE flip_green_channel=true','source':'authored seeded microrelief; structural chevrons, braids, panel reveals and seams are real geometry','complete':True},indent=2),encoding='utf-8')
print('LEIXI_PBR_MAPS_AUTHORED')
