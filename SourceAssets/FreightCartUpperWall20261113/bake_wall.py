"""Registered 4.32 m surface atlas; centimetres follow the original wall, with a shared depth field for the mesh."""
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates, gaussian_filter
R=Path(__file__).resolve().parent
scanroot=R.parent/'DungeonWallUpgrade20260924/Authored/Textures'
chiproot=R.parent/'FacilityQuixel20261108/Sources/DamagedConcrete/Textures'
W,H=2048,1024
lo,hi=-548.,-116.
bottom,top=86.8,319.55
y,z=np.meshgrid(lo+(np.arange(W,dtype=np.float32)+.5)*(hi-lo)/W,top-(np.arange(H,dtype=np.float32)+.5)*(top-bottom)/H)
rng=np.random.default_rng(4721)
def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
def field(h,w):
    data=rng.normal(size=(h,w)).astype(np.float32)
    return np.asarray(Image.fromarray(data).resize((W,H),Image.Resampling.BICUBIC))
def source(path):
    im=Image.open(path)
    if im.mode in ('RGBA','RGB'):return np.asarray(im.resize((1024,1024),Image.Resampling.LANCZOS),dtype=np.float32)/255
    data=np.asarray(im.resize((1024,1024),Image.Resampling.BILINEAR),dtype=np.float32)
    return (data-data.min())/max(data.max()-data.min(),1e-6)
def project(src,U,V,wrap=True):
    if wrap:U,V=U%1,V%1
    uv=np.array([np.clip(V,0,1)*(src.shape[0]-1),np.clip(U,0,1)*(src.shape[1]-1)])
    if src.ndim==2:return map_coordinates(src,uv,order=1,mode='nearest')
    return np.stack([map_coordinates(src[:,:,i],uv,order=1,mode='nearest') for i in range(src.shape[2])],axis=-1)
def sampled(family,suffix,U,V):return project(source(scanroot/(family+'_'+suffix+'.png')),U,V)
def write(name,a):Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5)).save(R/(name+'.png'))
macro=field(7,12);mid=field(31,61);fine=field(100,192)
vertical=field(8,160)
# Original mineral finish and aggregate share the same transform across color, normal, and roughness.
U=(y-lo)/123+.12;V=(top-z)/123+.33
fineU=(y-lo)/67+.34;fineV=(top-z)/67+.19
base=sampled('Wall','BaseColor',U,V);grit=sampled('FabSection','BaseColor',fineU,fineV)
norm=sampled('Wall','Normal',U,V)[:,:,:2]*2-1;gn=sampled('FabSection','Normal',fineU,fineV)[:,:,:2]*2-1
rock=sampled('Wall','ORM',U,V);gr=sampled('FabSection','ORM',fineU,fineV)
mine=base.mean(2);aggregate=grit.mean(2)
# Thin paste is worn through unevenly; aggregate remains mineral grey rather than wet or sooty.
coverage=.19+.55*smooth(-.85,.88,mid*.67+macro*.37)
rough=.61+.26*rock[:,:,1]+.04*coverage+.017*mid
ao=.84+.16*rock[:,:,0]
nxy=norm*.59+gn*(.32+.82*coverage[:,:,None])
body=.531+.96*(mine-.536)+(aggregate-.476)*(.39+coverage*.96)+.021*macro+.009*mid+.010*vertical
# Edge seams follow the cast courses and the cap joints. A line seldom stays equally dark end to end.
lower=z<200
dy=np.minimum(np.abs(y+np.where(lower,402.,429.)),np.abs(y+np.where(lower,265.,278.)))
dy=abs(dy+(.11*fine+.055*mid))
dz=abs(z-200.+.10*fine+.08*mid)
gap=np.minimum(dy,dz)
seam=(1-smooth(.15,.67,gap))*(.82+.16*smooth(-1,1,mid))
rim=np.exp(-((gap-.92)/.47)**2)
body-=seam*.137+np.exp(-gap/2.0)*.017
body+=rim*.018
body+=np.where(lower,np.where(y<-402,.003,np.where(y<-265,-.016,.006)),np.where(y<-429,-.009,np.where(y<-278,.012,-.004)))
# Casting tie marks are shallow paired pockets, spaced by formwork. Some were filled flush.
for yy,zz,amount in [(-523,175,.75),(-423,176,.70),(-379,109,.62),(-287,174,.72),(-243,108,.49),(-140,175,.76),(-406,222,.66),(-299,226,.51),(-252,288,.66),(-146,226,.55)]:
    ds=np.hypot(y-yy,z-zz)
    body-=amount*.085*(1-smooth(.74,1.28,ds))
    body+=.016*np.exp(-((ds-1.43)/.31)**2)
# Broken paste: irregular elongated edge loss, one smaller flake by the return and a few sparse pinholes.
chip=np.zeros_like(y)
for yy,zz,sy,sz,amp in [(-398,187,8.6,14.3,1),(-402.6,198,10.5,4.1,.89),(-386.5,196,4.5,2.6,.76),(-261,132,4.7,8.9,.9),(-277.4,255,7.7,4.0,.78),(-157,98,5.1,3.5,.85),(-460,104,3.8,1.9,.78)]:
    radius=np.hypot((y-yy)/sy,(z-zz)/sz)
    irregular=.19*mid+.15*fine+.22*(aggregate-.476)*5
    chip=np.maximum(chip,amp*(1-smooth(.71,1.00,radius-irregular)))
chipcol=project(source(next(chiproot.glob('*B-O.png'))),.38+.44*(fineU%1),.64+.20*(fineV%1),False)[:,:,:3].mean(2)
# Grain base, fracture core and unbroken ledge have separate responses to grazing light.
core=np.clip(.390+(aggregate-.476)*1.6+.62*(chipcol-.34)+.011*mid,.25,.51)
body=body*(1-chip)+core*chip
lip=np.maximum(gaussian_filter(chip,2.1)-chip,0)
body+=lip*.27
rough=rough*(1-chip)+(.76+.19*gr[:,:,1])*chip
ao=np.minimum(ao,1-.17*chip-.18*seam)
gx=np.gradient(chip,axis=1)*(W/(hi-lo));gz=-np.gradient(chip,axis=0)*(H/(top-bottom))
nxy[:,:,0]+=np.clip(gx,-1,1)*.36
nxy[:,:,1]+=np.clip(gz,-1,1)*.36
nxy=np.clip(nxy,-.8,.8);n3=np.dstack([nxy,np.ones_like(body)]);n3/=np.linalg.norm(n3,axis=2)[:,:,None]
tint=np.array([1.034,1.010,.976],np.float32)
write('T_CastBay_Color',body[:,:,None]*tint)
write('T_CastBay_Normal',n3*.5+.5)
write('T_CastBay_ORM',np.dstack([ao,np.clip(rough,.58,.98),np.zeros_like(body)]))
# Displacement positions the original wall behind the recess. Saved height is centimetres facing the aisle.
depth=1.72-.82*seam-.95*chip+.14*mid+.09*(mine-.536)*5
np.save(R/'wall-depth.npy',np.asarray(Image.fromarray(depth.astype('float32')).resize((433,234),Image.Resampling.BILINEAR)))
