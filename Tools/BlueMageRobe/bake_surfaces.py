"""Bake deterministic cloth and embroidered relief from one physical height field."""
import json,math
from pathlib import Path
import numpy as np
from PIL import Image
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018';T=R/'Textures';T.mkdir(exist_ok=True)
def save(name,array):Image.fromarray(np.uint8(np.clip(array,0,1)*255+.5)).save(T/(name+'.png'))
def weave(x,y):
    warp=np.cos(math.tau*x/.042);weft=np.cos(math.tau*y/.042);alternate=np.cos(math.pi*x/.042)*np.cos(math.pi*y/.042)
    h=.0016*(warp+weft)+.0009*alternate+.00028*np.sin(x*184+y*107)
    color=.96+.026*warp+.026*weft+.018*np.sin(x*11.3+y*4.1)
    return h,color
def normal(height,width_cm,height_cm):
    dy,dx=np.gradient(height,height_cm/height.shape[0],width_cm/height.shape[1]);n=np.stack([-dx,-dy,np.ones_like(dx)],axis=-1);n/=np.linalg.norm(n,axis=-1,keepdims=True)
    return n*.5+.5
def outputs(name,height,color,rough,metal,physical):
    save('T_'+name+'_BaseColor',color);save('T_'+name+'_Normal',normal(height,*physical))
    ao=np.clip(1-np.maximum(0,-height)*6,.85,1);save('T_'+name+'_ORM',np.stack([ao,np.broadcast_to(rough,height.shape),np.broadcast_to(metal,height.shape)],-1))
    Image.fromarray(np.uint16(np.clip((height+.005)/.025,0,1)*65535)).save(T/('T_'+name+'_Height.png'))
    np.save(T/(name+'_height_cm.npy'),height.astype('float32'))
u,v=np.meshgrid(np.arange(1024)/1024,np.arange(1024)/1024);h,c=weave(u*4,v*4);blue=np.array([.07,.22,.55]);outputs('BlueMageFabric',h,c[...,None]*blue,.86-.02*c,0,(4,4))

# A repeatable band: stitched edges, fine vine lines, and small eight-point marks.
u,v=np.meshgrid(np.arange(2048)/2048,np.arange(512)/512);h,c=weave(u*22,v*3.5);x=(u*8)%1
distance=np.full_like(u,10.)
for y in (.09,.15,.85,.91):distance=np.minimum(distance,np.abs(v-y))
distance=np.minimum(distance,np.abs(v-(.5+.19*np.sin(math.tau*x))))
distance=np.minimum(distance,np.abs(v-(.5-.19*np.sin(math.tau*x))))
star=[]
for i in range(16):
    angle=math.tau*i/16;r=.28 if i%2==0 else .11;star.append(np.array([.5+r*math.cos(angle),.5+r*math.sin(angle)]))
for a,b in zip(star,star[1:]+star[:1]):
    dx=b[0]-a[0];dy=b[1]-a[1];tt=np.clip(((x-a[0])*dx+(v-a[1])*dy)/(dx*dx+dy*dy),0,1)
    distance=np.minimum(distance,np.sqrt((x-a[0]-tt*dx)**2+(v-a[1]-tt*dy)**2))
thread=np.exp(-(distance/.0085)**2);stitch=np.exp(-((v-.035)/.006)**2)+np.exp(-((v-.965)/.006)**2);stitch*=np.maximum(0,np.sin(u*math.tau*110))
mask=np.clip(thread+.7*stitch,0,1);h+=.012*thread+.007*stitch;silver=np.array([.69,.67,.61]);color=c[...,None]*blue*(1-mask[...,None])+silver*mask[...,None]
outputs('BlueMageEmbroidery',h,color,.84*(1-mask)+.40*mask,.65*mask,(22,3.5))
(R/'surface_source.json').write_text(json.dumps(dict(fabric_tile_cm=4,embroidery_band_cm=[22,3.5],normal_convention='OpenGL tangent space; UE import flip green',fabric_relief_cm=.005,embroidery_relief_cm=.019,bake_source='Analytic woven and stitch height fields; same fields saved as physical high-surface data',textures=[p.name for p in sorted(T.glob('*.png'))]),indent=2),encoding='utf-8')
print('BLUE_ROBE_PBR_SURFACES_BAKED',flush=True)
