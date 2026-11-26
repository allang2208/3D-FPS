"""Physical twill and raised embroidery fields; no directional lighting baked in."""
import json, math
from pathlib import Path
import numpy as np
from PIL import Image
R=Path('D:/FPS3D/FPSGAME/SourceAssets/BlueMageRobe20261018/FPSoftSleeves20261020')
T=R/'Textures';T.mkdir(parents=True,exist_ok=True)
def save(name,array):
    Image.fromarray(np.uint8(np.clip(array,0,1)*255+.5)).save(T/(name+'.png'))
def weave(x,y):
    spacing=.0625
    warp=(.5+.5*np.cos(math.tau*x/spacing))**2
    weft=(.5+.5*np.cos(math.tau*y/spacing))**2
    diagonal=np.sin(math.tau*(x-y)/(spacing*4))
    slub=np.sin(math.tau*x/2)*np.sin(math.tau*y/8)+.3*np.sin(math.tau*(x+y)/4)
    height=.0042*(warp*(.65+.35*diagonal)+weft*(.65-.35*diagonal))+.0006*slub
    value=1+.025*slub+.018*(warp-weft)
    rough=.86+.035*slub-.035*(warp+weft)
    return height,value,rough
def output(name,h,color,rough,metal,span):
    dy,dx=np.gradient(h,span[1]/h.shape[0],span[0]/h.shape[1])
    n=np.stack((-dx,-dy,np.ones_like(h)),-1);n/=np.linalg.norm(n,axis=-1,keepdims=True)
    save('T_'+name+'_BaseColor',color);save('T_'+name+'_Normal',n*.5+.5)
    ao=np.clip(1-(h.max()-h)*9,.84,1)
    save('T_'+name+'_ORM',np.stack((ao,np.broadcast_to(rough,h.shape),np.broadcast_to(metal,h.shape)),-1))
    np.save(T/(name+'_height_cm.npy'),h.astype('float32'))
blue=np.array([.075,.205,.48])
u,v=np.meshgrid(np.arange(2048,dtype='float32')/2048,np.arange(2048,dtype='float32')/2048)
h,value,rough=weave(u*8,v*8)
output('RobeSoftTwill',h,value[...,None]*blue,rough,0,(8,8))
u,v=np.meshgrid(np.arange(2048,dtype='float32')/2048,np.arange(512,dtype='float32')/512)
h,value,rough=weave(u*22,v*3.5);x=(u*8)%1
distance=np.full_like(u,10.)
for y in (.09,.15,.85,.91):distance=np.minimum(distance,np.abs(v-y))
for sign in (-1,1):distance=np.minimum(distance,np.abs(v-(.5+sign*.19*np.sin(math.tau*x))))
star=[np.array([.5+(.28 if i%2==0 else .11)*math.cos(math.tau*i/16),
               .5+(.28 if i%2==0 else .11)*math.sin(math.tau*i/16)]) for i in range(16)]
for a,b in zip(star,star[1:]+star[:1]):
    delta=b-a;t=np.clip(((x-a[0])*delta[0]+(v-a[1])*delta[1])/np.dot(delta,delta),0,1)
    distance=np.minimum(distance,np.sqrt((x-a[0]-t*delta[0])**2+(v-a[1]-t*delta[1])**2))
thread=np.exp(-(distance/.009)**2)
stitch=(np.exp(-((v-.035)/.006)**2)+np.exp(-((v-.965)/.006)**2))*np.maximum(0,np.sin(u*math.tau*110))**2
mask=np.clip(thread+.7*stitch,0,1)
filament=.94+.06*np.sin(u*math.tau*440+v*math.tau*16)
h+=.015*thread*filament+.008*stitch
silver=np.array([.64,.63,.59])
color=value[...,None]*blue*(1-mask[...,None])+silver*filament[...,None]*mask[...,None]
output('RobeSoftCuff',h,color,rough*(1-mask)+.46*mask,.68*mask,(22,3.5))
(R/'surface_source.json').write_text(json.dumps(dict(completed=True,
    fabric_tile_cm=8,yarn_spacing_cm=.0625,fabric_relief_cm=.006,
    embroidery_band_cm=[22,3.5],normal_convention='OpenGL; UE flips green',
    source='Analytic physical twill yarn and embroidery height fields saved as float32',
    runtime_tested=False),indent=2),encoding='utf-8')
print('SOFT_ROBE_SURFACES_BAKED',flush=True)
