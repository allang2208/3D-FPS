"""Prepare aligned color, DirectX normals and AO/roughness/height from licensed scan channels."""
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
from scipy.interpolate import RectBivariateSpline

ROOT=Path(__file__).resolve().parents[3]/'SourceAssets/TemperateHillsOldChapel/Concept01/Surfaces'
OUT=ROOT/'Prepared'
OUT.mkdir(exist_ok=True)
def read(asset, spec):
    return np.asarray(Image.open(ROOT/asset/spec),dtype=np.float32)
def load(asset):
    rgb=read(asset,'diff.jpg')/255
    n=read(asset,'nor_dx.png')/127.5-1
    arm=read(asset,'arm.jpg')/255
    h=read(asset,'disp.png')
    low,high=np.percentile(h,[1,99])
    h=np.clip((h-low)/(high-low),0,1)
    return rgb,n,arm,h
def field(scale,seed,size):
    rng=np.random.default_rng(seed)
    grid=rng.random((scale,scale)).astype('f')
    grid=np.tile(grid,(3,3))
    axes=np.arange(3*scale);query=scale+np.arange(size)*scale/size
    return RectBivariateSpline(axes,axes,grid)(query,query).astype('f')
def mix(a,b,w):
    if a.ndim==3:w=w[:,:,None]
    return a*(1-w)+b*w
def write(role,rgb,n,arm,h):
    def png(channel,a):
        Image.fromarray(np.round(np.clip(a,0,1)*255).astype('uint8')).save(OUT/(role+'_'+channel+'.png'),compress_level=3)
    png('Color',rgb)
    n/=np.maximum(np.linalg.norm(n,axis=2,keepdims=True),.00001)
    png('NormalDX',n*.5+.5)
    png('ARH',np.stack([arm[:,:,0],arm[:,:,1],h],axis=2))
    # The low-frequency scan drives real mesh relief. Preserve small-scale detail in the shader.
    grid=Image.fromarray(gaussian_filter(h,6,mode='wrap')).resize((256,256),Image.Resampling.BOX)
    np.save(OUT/(role+'_Relief.npy'),np.asarray(grid,dtype='f4'))
stone,sn,sa,sh=load('old_stone_wall')
write('Wall',stone,sn,sa,sh)
plaster,pn,pa,ph=load('plaster_stone_wall_02')
size=sh.shape[0]
wear=.51*field(3,106,size)+.25*field(8,221,size)+.16*field(27,9,size)+.08*field(77,98,size)
mask=np.clip((wear+.14*(ph-.5)-.43)/.14,0,1)
mask=mask*mask*(3-2*mask)
# The surviving lime has a muted warm chalk tone. Cavities remain deep where it flakes away.
pale=np.clip(plaster*np.array([1.10,1.08,1.035],dtype='f4')+.026,0,1)
height=mix(sh*.74,.34+.61*ph,mask)
normal=mix(sn,pn,mask)
# Add the narrow rolled edge of the plaster as well as both source normals (DX has image-down Y).
rise=gaussian_filter(mask,2.,mode='wrap')
normal[:,:,0]-=.75*(np.roll(rise,-1,1)-np.roll(rise,1,1))
normal[:,:,1]-=.75*(np.roll(rise,-1,0)-np.roll(rise,1,0))
write('Limewash',mix(stone,pale,mask),normal,mix(sa,pa,mask),height)
for role,asset in [('Flagstone','monastery_stone_floor'),('Timber','rough_wood')]:
    rgb,n,arm,h=load(asset)
    if role=='Timber':rgb=rgb*np.array([.87,.805,.725],dtype='f4')
    write(role,rgb,n,arm,h)

