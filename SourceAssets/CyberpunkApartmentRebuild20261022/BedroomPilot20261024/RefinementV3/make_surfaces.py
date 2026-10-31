"""Deterministic authored PBR for paper fibres, page edges, glaze, soil and leaf veins.
Height-derived tangent normals use physical units and DirectX green convention.
Existing scan textures remain the wood/metal/textile sources.
"""
from pathlib import Path
import numpy as np,json
from PIL import Image
R=Path(__file__).resolve().parent;O=R/'Textures';O.mkdir(exist_ok=True)
S=2048;rng=np.random.default_rng(31024)
y,x=np.mgrid[0:S,0:S].astype(np.float32)/S
def noise(scale):
    # Fourier bandlimited periodic noise, no copyrighted image inputs.
    result=np.zeros((S,S),np.float32)
    for _ in range(14):
        a,b=rng.integers(max(1,scale//3),scale+1,2);p=rng.uniform(0,np.pi*2)
        result+=np.sin(2*np.pi*(a*x+b*y)+p).astype(np.float32)/14
    return result
n0=noise(9);n1=noise(63);n2=noise(380);grain=rng.random((S,S),dtype=np.float32)-.5
records=[]
def save(key,height,bc,rough,period,ao=None):
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))/(2*period/S)
    dy=(np.roll(height,-1,0)-np.roll(height,1,0))/(2*period/S)
    normal=np.stack([-dx,dy,np.ones_like(dx)],axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    color=np.clip(bc,0,1);srgb=np.where(color<=.0031308,color*12.92,1.055*color**(1/2.4)-.055)
    orm=np.stack([np.ones_like(x) if ao is None else ao,np.clip(rough,0,1),np.zeros_like(x)],-1)
    for suffix,data in [('BC',srgb),('N',normal*.5+.5),('ORM',orm)]:
        Image.fromarray(np.round(np.clip(data,0,1)*255).astype(np.uint8)).save(O/f'T_BP3_{key}_{suffix}.png')
    records.append(dict(family=key,size=S,period_m=period,height_peak_to_peak_mm=float(np.ptp(height)*1000),normal_xy_rms=float(np.sqrt(np.mean(normal[:,:,:2]**2))),source='Original analytical surface; not scanned'))
fibres=(np.sin((y*790+n0*.3)*np.pi*2)*.3+n2*.6+grain*.12)
h=(n1*.6+fibres)*.000032
save('Paper',h,np.stack([.65+n0*.025+fibres*.012,.61+n0*.022+fibres*.010,.49+n0*.020+fibres*.008],-1),.79+n1*.08+fibres*.035,.10)
pages=.5+.5*np.cos(2*np.pi*(y*312+n0*.12))
h=pages**7*.000045+n2*.000006
save('Pages',h,np.stack([.68-pages*.075+n1*.02,.64-pages*.07+n1*.018,.52-pages*.06+n1*.016],-1),.79+pages*.07,.10)
h=(n1*.34+n2*.16+np.sin(y*np.pi*2*46)*.09)*.00006
speckles=np.maximum(0,grain-.475)*3
save('Ceramic',h,np.stack([.43+n0*.05-speckles,.46+n0*.05-speckles,.39+n0*.04-speckles],-1),.30+n0*.08+n2*.12,.12)
soil=(n0*.4+n1*.5+n2*.3)
h=soil*.0015
save('Soil',h,np.stack([.06+soil*.05,.035+soil*.03,.018+soil*.014],-1),.91+soil*.07,.15,np.clip(.88+soil*.22,.6,1))
mid=np.exp(-((x-.5)/.017)**2)
vein_phase=np.abs(x-.5)*1.15-y*7
veins=np.exp(-(np.sin(vein_phase*np.pi)/.10)**2)*(1-np.abs(x-.5)*1.4)
h=mid*.00025+veins*.00009+n2*.000007
edge=np.clip(np.abs(x-.5)*2,0,1)
green=(.4+.6*np.sin(np.pi*y))*(1-.25*edge)
bc=np.stack([.045+green*.05+veins*.018,.10+green*.12+veins*.026,.021+green*.035+veins*.008],-1)
save('Leaf',h,bc,.43+n0*.08+veins*.05,.08)
(R/'texture-source.json').write_text(json.dumps(records,indent=2),encoding='utf8')
print('PBR_SURFACES_WRITTEN',len(records),'families',S)
