"""Build a single colour, tangent normal and ORM atlas for the tavern's drying rail."""
from pathlib import Path
import numpy as np
from PIL import Image

root=Path(__file__).resolve().parents[4]
sources=root/'SourceAssets'
out=sources/'HillsVillageTavern/DryingRack'
out.mkdir(parents=True,exist_ok=True)
side=512
rng=np.random.default_rng(921144)
y,x=np.mgrid[0:side,0:side]/side
tau=2*np.pi
def noise(w,h):
    small=Image.fromarray(rng.integers(0,256,(h,w),dtype=np.uint8))
    return (np.asarray(small.resize((side,side),Image.Resampling.BICUBIC),float)-127.5)/127.5

def source(path):
    return np.asarray(Image.open(path).convert('RGB').resize((side,side),Image.Resampling.LANCZOS)).copy()

def rgb01(array):
    return np.uint8(255*np.clip(array,0,1))

def with_color(tint,variation,channel_tint=None):
    return np.uint8(np.clip(np.asarray(tint)[None,None,:]*(1+variation[:,:,None])+
                            (0 if channel_tint is None else channel_tint),0,255))

def packed(height,rough,metal=0,strength=1.0):
    dy,dx=np.gradient(height)
    nx,ny=-dx*strength,-dy*strength
    length=np.sqrt(nx**2+ny**2+1)
    normal=rgb01(np.stack([.5+.5*nx/length,.5+.5*ny/length,.5+.5/length],-1))
    orm=rgb01(np.stack([np.clip(.96+.16*(height-np.mean(height)),.65,1),
                        np.broadcast_to(rough,height.shape),np.full_like(height,metal)],-1))
    return normal,orm

tiles=[]
chapel=sources/'TemperateHillsOldChapel/Concept01/Surfaces/Prepared'
timber=[source(chapel/name) for name in ('Timber_Color.png','Timber_NormalDX.png','Timber_ARH.png')]
timber[2][:,:,2]=0
tiles.append(timber)
cloud,grain=noise(14,22),noise(226,251)
twist=np.cos(tau*(7*x-6*y+.10*cloud))
fibre=np.sin(tau*(49*x-41*y+.38*noise(35,31)))
rope_height=.35*twist+.08*fibre+.055*grain
tiles.append((with_color((138,109,73),.13*cloud+.12*twist+.045*fibre+.045*grain),
              *packed(rope_height,.86+.035*cloud, strength=2.4)))
for onion in (False,True):
    fibres=noise(174,8)
    body=noise(19,7)
    striation=np.cos(tau*(23*x+.16*np.sin(tau*y)+.1*body))**7
    peel=np.maximum(0,noise(17,8)-.45)*(.5+y)
    base=(169,104,48) if onion else (208,193,155)
    shade=.078*body+.06*striation+.049*fibres-.15*peel+.024*grain
    undertone=(np.stack([2*body, -4*body, -7*body],-1) if onion else
               np.stack([2*body,-2*body,4*body],-1))
    h=.19*striation+.13*fibres+.16*peel+.032*grain
    tiles.append((with_color(base,shade,undertone),*packed(h,.56+.10*body+.08*peel,strength=1.65)))
leafnoise=noise(30,38)
vein=(np.maximum(0,1-np.abs(np.sin(tau*(6*y-2.3*np.abs(x-.5)+.11*leafnoise)))*5)*
      np.maximum(0,1-1.35*np.abs(x-.5)))
midrib=np.exp(-((x-.5+.009*np.sin(tau*y))/.021)**2)
edge=np.abs(x-.5)**2*3
leafshade=.17*cloud+.052*grain+.13*vein+.16*midrib-.085*edge
tiles.append((with_color((102,109,67),leafshade),*packed(.18*vein+.30*midrib+.06*leafnoise,.84+.034*cloud,strength=1.35)))
straw=noise(124,8)
streak=.9*straw+.35*noise(18,6)
tiles.append((with_color((153,129,79),.17*streak+.06*grain),*packed(.18*streak+.06*grain,.81+.05*straw,strength=1.7)))
old=sources/'HillsVillageTavern/Furniture'
worn_base=source(old/'RottenWoodSurface_00A_BaseColor.png')
worn_normal=source(old/'RottenWoodSurface_00A_Normal.png')
worn_mask=source(old/'RottenWoodSurface_00A_RHAOM.png')
tiles.append((worn_base,worn_normal,np.stack([worn_mask[:,:,2],worn_mask[:,:,0],np.zeros_like(worn_mask[:,:,0])],-1)))
scale=noise(61,68)
rust=np.clip((cloud+scale*.5-.18)*1.8,0,1)
metal_base=with_color((69,63,52),.17*scale+.2*grain,np.stack([19*rust,4*rust,-3*rust],-1))
metal_normal,metal_mask=packed(.23*scale+.08*grain,.43+.24*rust+.08*grain,.77,2)
cut=sources/'HillsVillageCarpenter/Props/Authored'
tile=[metal_base,metal_normal,metal_mask]
for image,suffix in zip(tile,('Color','Normal','ORM')):
    donor=source(cut/('Cut_'+suffix+'.png'))
    image[:,side//2:]=np.asarray(Image.fromarray(donor).resize((side//2,side),Image.Resampling.LANCZOS))
tiles.append(tile)
for channel,label in enumerate(('Color','Normal','ORM')):
    atlas=Image.new('RGB',(side*4,side*2))
    for index,part in enumerate(tiles):
        atlas.paste(Image.fromarray(part[channel]),((index%4)*side,(index//4)*side))
    atlas.save(out/('T_TavernDryGoods_'+label+'.png'))
