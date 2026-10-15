"""Seamless directional turbulence and a thin three-layer spherical shock front."""
import json,math
from pathlib import Path
import numpy as np
from scipy.ndimage import map_coordinates
from PIL import Image
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HeQueBoss20261014/PsychicWaveV02')
for folder in ('Authoring','Export','Textures','Records','Before'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
W,H=1024,512
u=np.linspace(0,1,W,dtype=np.float32);v=np.linspace(0,1,H,dtype=np.float32)
longitude,latitude=np.meshgrid(u*math.tau,v*math.pi)
direction=np.stack((np.sin(latitude)*np.cos(longitude),np.sin(latitude)*np.sin(longitude),np.cos(latitude)))
rng=np.random.default_rng(151516)
grid=rng.random((48,48,48),dtype=np.float32)
def field(pos,frequency,shift):
    coordinates=pos*frequency+np.array(shift,dtype=np.float32)[:,None,None]
    return map_coordinates(grid,coordinates,order=3,mode='grid-wrap',prefilter=True)
warp=np.stack([field(direction,5,shift) for shift in ((15,19,23),(27,13,32),(32,24,18))])-.5
bent=direction+warp*.44
density=np.zeros((H,W),dtype=np.float32);total=0.
for frequency,gain in ((5,1.),(11,.55),(23,.26),(43,.11)):
    density+=gain*field(bent,frequency,(24,24,24));total+=gain
density/=total
def remap(a,lo=2,hi=98):
    mn,mx=np.percentile(a,[lo,hi]);return np.clip((a-mn)/max(1e-6,mx-mn),0,1)
density=remap(density)
fold=field(direction+warp*.76,12,(21,31,17))
filament=np.exp(-((fold-.49)/.052)**2)*(.35+.65*density)
detail=remap(field(bent,35,(12,27,33)))
packed=np.stack((density,filament,detail),axis=-1)
# Explicit wrap identity, including the polar rows. The source is a 3D field
# sampled on a sphere, not a tiled checker pattern projected onto a UV sphere.
packed[:,-1]=packed[:,0];packed[0,:]=packed[0,0];packed[-1,:]=packed[-1,0]
Image.fromarray(np.rint(packed*255).astype(np.uint8),'RGB').save(ROOT/'Textures/T_HeQue_PsychicFlowV02.png')
report=dict(texture=[W,H],channels=dict(R='warped broad density',G='folded fine filaments',B='fine erosion'),
    shape='three smooth shells; binary vertex RG = 00 front, 10 flow, 11 wake',
    layer_offsets_cm=[0,18,55],radius_cm=1000,wave_seconds=.36,fade_seconds=.24,
    turn_speed_degrees_per_second=120,seed=151516,gameplay_tested=False,rendered=False)
(ROOT/'Records/authoring.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('HEQUE_PSYCHIC_FLOW_AUTHORED '+json.dumps(report),flush=True)
