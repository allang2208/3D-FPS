"""Write the actual long-atlas PBR maps, preserving the fine 2011 finish."""
import argparse,json,shutil
from pathlib import Path
import numpy as np
from PIL import Image
from surface_recipe import scale_fields

O=Path(__file__).parent;T=O/'Textures';T.mkdir(exist_ok=True)
args=argparse.ArgumentParser();args.add_argument('--width',type=float,required=True);args.add_argument('--height',type=float,required=True)
config=args.parse_args();N=2048;yy,xx=np.mgrid[0:N,0:N].astype(np.float32);u,v=(xx+.5)/N,(yy+.5)/N
body,lip,hatch,var=scale_fields(u,v,config.width,config.height)
noise=np.random.default_rng(20111003).random((N,N),dtype=np.float32)
height=body*.000075+lip*.000045+hatch*.0000015+(noise-.5)*.0000003
dx=np.gradient(height,config.width/N,axis=1);dy=np.gradient(height,config.height/N,axis=0)
normal=np.stack([-dx,-dy,np.ones_like(dx)],axis=-1);normal/=np.linalg.norm(normal,axis=-1)[...,None]
tone=.0185+.0032*body+.0012*var+.00018*(noise-.5)
color=np.stack([tone*.98,tone,tone*1.025],axis=-1)
orm=np.stack([.94+.06*body,.62-.045*body+.008*var,np.zeros_like(body)],axis=-1)
private={};legacy={}
for kind,arr in [('BaseColor',color),('Normal',normal*.5+.5),('ORM',orm),('Height',np.repeat((height/.00013)[...,None],3,axis=-1))]:
    arr=np.clip(arr,0,1)
    if kind=='BaseColor':arr=np.where(arr<=.0031308,arr*12.92,1.055*arr**(1/2.4)-.055)
    file=T/('T_PV2011_ViperQuiet_'+kind+'.png')
    Image.fromarray(np.clip(np.flipud(arr)*255+.5,0,255).astype(np.uint8)).save(file)
    compatible=T/('T_PitViper2011_VipViperGrip_'+kind+'.png');shutil.copy2(file,compatible)
    legacy[kind]=str(compatible)
    if kind!='Height':private[kind]=str(file)
recipe={'private':private,'legacy':legacy,'width_m':config.width,'height_m':config.height,'resolution':N,
    'normal_source_convention':'OpenGL; flip green once during UE import',
    'design':'native-outline longitudinal scale fields; fine quiet finish','game_tested':False,'acceptance_rendered':False}
(O/'texture_recipe.json').write_text(json.dumps(recipe,indent=2),encoding='utf8')
print('VIP_LONGITUDINAL_PBR_TEXTURES_SAVED',flush=True)
