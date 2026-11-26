"""Physical twill and leather relief fields for the approved ranger top."""
import json, math
from pathlib import Path
import numpy as np
from PIL import Image
R=Path('D:/FPS3D/FPSGAME/SourceAssets/FieldRangerTop20261020');T=R/'Textures'
T.mkdir(parents=True,exist_ok=True)
N=2048;span=8.;v,u=np.mgrid[:N,:N].astype('float32')/N
def save(name,x):Image.fromarray(np.uint8(np.clip(x,0,1)*255+.5)).save(T/(name+'.png'))
def output(name,h,c,r):
    dx=(np.roll(h,-1,1)-np.roll(h,1,1))/(2*span/N)
    dy=(np.roll(h,-1,0)-np.roll(h,1,0))/(2*span/N)
    normal=np.stack((-dx,-dy,np.ones_like(dx)),axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    save(name+'_BaseColor',c);save(name+'_Normal',normal*.5+.5)
    save(name+'_ORM',np.stack((np.clip(1-(h.max()-h)*8,.86,1),np.clip(r,.25,.95),np.zeros_like(h)),-1))
    np.save(T/(name+'_height_cm.npy'),h)
warp=(.5+.5*np.cos(math.tau*u*160))**2;weft=(.5+.5*np.cos(math.tau*v*160))**2
diag=np.sin(math.tau*(u-v)*40);slub=np.sin(math.tau*u*3)*np.sin(math.tau*v*5)
h=.0035*(warp*(.65+.35*diag)+weft*(.65-.35*diag))+.0005*slub
output('RangerTwill',h,np.array([.31,.33,.245])*(1+.038*slub+.022*(warp-weft))[...,None],.81+.035*slub-.025*(warp+weft))
rng=np.random.default_rng(8124)
grain=np.zeros_like(u);broad=np.zeros_like(u)
for i in range(18):
    x,y=rng.integers(35,125,size=2);phase=rng.uniform(0,math.tau)
    grain+=np.sin(math.tau*(x*u+y*v)+phase)/18
for i in range(7):
    x,y=rng.integers(1,8,size=2);broad+=np.sin(math.tau*(x*u+y*v)+rng.uniform(0,math.tau))/7
pores=np.maximum(0,grain-.22)**2
h=.009*grain-.035*pores+.002*broad
output('RangerLeather',h,np.array([.34,.235,.165])*(1+.16*broad+.12*grain)[...,None],.57+.09*broad-.08*grain)
(R/'surfaces.json').write_text(json.dumps(dict(completed=True,tile_cm=8,texture_size=2048,
    normal_convention='OpenGL; UE import flips green',materials=['RangerTwill','RangerLeather'],
    physical_height_fields=True,runtime_tested=False),indent=2),encoding='utf-8')
print('RANGER_PBR_BAKED',flush=True)
