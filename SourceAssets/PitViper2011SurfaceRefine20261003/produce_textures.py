"""Author numeric PBR maps with quiet microfinish and preserved grip relief."""
import json,math,shutil
from pathlib import Path
import numpy as np
from PIL import Image

O=Path(__file__).parent;P=O.parents[1];T=O/'Textures';T.mkdir(exist_ok=True)
textures={}

def write(name,data,color=False,flip=False):
    data=np.clip(data,0,1)
    if color:data=np.where(data<=.0031308,data*12.92,1.055*data**(1/2.4)-.055)
    if flip:data=np.flipud(data)
    path=T/(name+'.png')
    Image.fromarray(np.clip(data*255+.5,0,255).astype(np.uint8)).save(path)
    return str(path)

# Small continuous directional machining variation. R feeds roughness only;
# no coloured speckles, pits, scratches or low-frequency blotches are added.
N=1024;yy,xx=np.mgrid[0:N,0:N].astype(np.float32)
rng=np.random.default_rng(20111003)
field=rng.standard_normal((N,N))
freq=np.fft.fftfreq(N)*N
window=np.exp(-.5*((freq[:,None]/165)**2+(freq[None,:]/13)**2));window[0,0]=0
field=np.fft.ifft2(np.fft.fft2(field)*window).real
field/=field.std()+1e-9
fine=.5+.011*field+.009*np.sin(yy/N*math.tau*270)+.005*np.sin(yy/N*math.tau*413+xx/N*math.tau*3)
grain=np.stack([np.clip(fine,.43,.57),np.full_like(fine,.5),np.zeros_like(fine),np.full_like(fine,.375)],-1)
textures['Grain']=write('T_PV2011_QuietMachining_Grain',grain)
textures['TacticalMetal']={
    'BaseColor':write('T_PV2011_TacticalMetal_BaseColor',np.tile(np.array([.021,.023,.026],np.float32),(4,4,1)),color=True),
    'Roughness':write('T_PV2011_TacticalMetal_Roughness',np.full((4,4),.38,np.float32))}

# Preserve the three shared grip patterns at their original physical scale.
# Suppress random pigment/roughness speckles and only the superposed tiny relief.
x=xx/N*.1;y=yy/N*.1;rng=np.random.default_rng(19110927)
noise=rng.random((N,N),dtype=np.float32)
cells=120;gx=xx/N*cells;gy=yy/N*cells;ix=np.floor(gx).astype(int);iy=np.floor(gy).astype(int)
jitter=rng.random((cells,cells,2),dtype=np.float32);dist=np.full((N,N),100.,dtype=np.float32)
for dy in (-1,0,1):
    for dx in (-1,0,1):
        ox=jitter[(iy+dy)%cells,(ix+dx)%cells,0];oy=jitter[(iy+dy)%cells,(ix+dx)%cells,1]
        dist=np.minimum(dist,(gx-(ix+dx+ox))**2+(gy-(iy+dy+oy))**2)
granular=np.exp(-dist*8)
diamond=np.maximum(0,np.minimum(np.abs(np.sin(math.pi*(x+y)/.0025)),np.abs(np.sin(math.pi*(x-y)/.0025)))-.13)/.87
radius=np.sqrt(((x/.00125+.5)%1-.5)**2+((y/.00125+.5)%1-.5)**2)
dots=np.clip((.32-radius)/.15,0,1)
textures['Grips']={}
for key,pattern,depth,base,rough in [('pistol_grip_granular',granular,.000115,.024,.69),
    ('pistol_grip_diamond',diamond,.00018,.019,.64),('pistol_grip_quickdot',dots,.00007,.028,.60)]:
    height=pattern*depth+(noise-.5)*.0000008
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))/(.2/N)
    dy=(np.roll(height,-1,0)-np.roll(height,1,0))/(.2/N)
    normal=np.stack([-dx,-dy,np.ones_like(dx)],-1);normal/=np.linalg.norm(normal,axis=-1)[...,None]
    tone=base*(1+(noise-.5)*.006)
    color=np.stack([tone*.94,tone*.98,tone],-1)
    orm=np.stack([.93+.07*pattern,rough+(noise-.5)*.004,np.zeros_like(pattern)],-1)
    textures['Grips'][key]={kind:write('T_PV2011_'+key+'_'+kind,arr,color=kind=='BaseColor',flip=True)
        for kind,arr in [('BaseColor',color),('Normal',normal*.5+.5),('ORM',orm)]}

# Current VIP maps use the physically measured longitudinal skin atlas. Keep
# those exact maps on later quiet-finish production instead of regenerating
# the historical 42 mm patch atlas. Shared patterns above remain independent.
longitudinal=P/'SourceAssets/PitViper2011ViperLongitudinalGrip20261003/texture_recipe.json'
if longitudinal.exists():
    vip=json.loads(longitudinal.read_text(encoding='utf8'))['private'];textures['Vip']={}
    for kind,file in vip.items():
        dest=T/Path(file).name;shutil.copy2(file,dest);textures['Vip'][kind]=str(dest)
else:
    raise RuntimeError('Author the current longitudinal VIP grip before regenerating its quiet finish maps')
(O/'texture_recipe.json').write_text(json.dumps({'textures':textures,'grain_tile_cm':8,'scope':'2011 only',
    'grip_pattern_depths_preserved':True,'normal_source_convention':'OpenGL; flip green once on UE import',
    'texture_sizes':{'Grain':1024,'Grips':1024,'Vip':2048},'game_tested':False},ensure_ascii=False,indent=2),encoding='utf8')
print('PIT_VIPER_QUIET_SURFACE_TEXTURES_AUTHORED',len(textures['Grips']),flush=True)
