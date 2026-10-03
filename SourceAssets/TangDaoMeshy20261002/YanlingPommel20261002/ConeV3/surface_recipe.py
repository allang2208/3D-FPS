"""V3 physical metal response and sparse, shared geometry/PBR relief recipe."""
from pathlib import Path
import numpy as np
P = Path(__file__).resolve().parent
try:
    import bpy
    image = bpy.data.images.load(str(P/'Ornament/DragonCloud_HeightSource.png'))
    image.colorspace_settings.name = 'Non-Color'
    px = np.empty(image.size[0]*image.size[1]*4, np.float32)
    image.pixels.foreach_get(px)
    source = px.reshape(image.size[1], image.size[0], 4)[::-1].copy()
except ImportError:
    from PIL import Image, ImageFilter
    source = np.asarray(Image.open(P/'Ornament/DragonCloud_HeightSource.png').convert('RGBA'), dtype=np.float32)/255

def smooth(a,b,x):
    q=np.clip((x-a)/(b-a),0,1)
    return q*q*(3-2*q)

# Generated alpha includes a soft halo. Only the unlit carved ridges drive
# actual height/inlay; transparent halo does not become a raised panel.
lum=source[...,:3]@np.array([.2126,.7152,.0722],np.float32)
mask=smooth(.48,.72,lum)*smooth(.05,.4,source[...,3])
ys,xs=np.where(mask>.08)
ORN=np.stack([mask,lum],axis=2)[ys.min():ys.max()+1,xs.min():xs.max()+1]
CLOUD=ORN[:, :int(ORN.shape[1]*.255)]
# Continuous angular armour band around this rear panel; the polygon is also
# the boundary used to gate decoration, so there is no gold spill over it.
PANEL=[(.10,.045),(.90,.045),(.88,.22),(.71,.29),(.87,.38),(.50,.565),(.12,.48),(.28,.31),(.09,.235)]

def inside(x,y,poly=PANEL):
    x,y=np.asarray(x),np.asarray(y);out=np.zeros(np.broadcast(x,y).shape,dtype=bool)
    for i,(a,b) in enumerate(poly):
        c,d=poly[(i+1)%len(poly)]
        if abs(d-b)>1e-9:
            out^=((b>y)!=(d>y))&(x<(c-a)*(y-b)/(d-b)+a)
    return out

def sample(arr,x,y):
    x=np.clip(x,0,1)*(arr.shape[1]-1);y=np.clip(y,0,1)*(arr.shape[0]-1)
    x0=np.floor(x).astype(np.int32);y0=np.floor(y).astype(np.int32)
    x1=np.minimum(x0+1,arr.shape[1]-1);y1=np.minimum(y0+1,arr.shape[0]-1)
    fx,fy=(x-x0)[...,None],(y-y0)[...,None]
    return arr[y0,x0]*(1-fx)*(1-fy)+arr[y0,x1]*fx*(1-fy)+arr[y1,x0]*(1-fx)*fy+arr[y1,x1]*fx*fy

def ornament(s,t):
    # The long axis of the tiny dragon follows the cone axis, not its width.
    a,l=np.moveaxis(sample(ORN,(t-.075)/.445,(s-.15)/.70),-1,0)
    gate=smooth(.075,.11,t)*(1-smooth(.48,.53,t))*smooth(.12,.20,s)*(1-smooth(.80,.88,s))*inside(s,t)
    return a*gate,l

def height(s,t):
    a,l=ornament(s,t)
    return a*(.00014+.00013*l)

def frieze(u,v):
    # Real cloud engraving, wrapped by arc length around the ring/collar.
    # v spans the ring's full section. Front/back faces use the middle third.
    x=(np.asarray(u)*7)%1;y=(np.asarray(v)-.18)/.64
    a,l=np.moveaxis(sample(CLOUD,x,y),-1,0)
    gate=smooth(.16,.25,v)*(1-smooth(.75,.84,v))
    return a*gate,l

def linear_srgb(x):
    return np.where(x<=.0031308,12.92*x,1.055*np.maximum(x,0)**(1/2.4)-.055)

def save(family,key,a):
    Image.fromarray(np.clip(a*255+.5,0,255).astype('uint8')).save(P/'Textures'/f'TangDao_YanlingConeV3_{family}_{key}.png')

def normals(h,du,dv):
    dy,dx=np.gradient(h)
    nn=np.stack([-dx/du,dy/dv,np.ones_like(h)],2)
    nn/=np.linalg.norm(nn,axis=2)[...,None]
    return nn*.5+.5

def noise(n,small,seed):
    rng=np.random.default_rng(seed)
    im=Image.fromarray((rng.random((small,small))*255).astype('uint8')).resize((n,n),Image.Resampling.BICUBIC)
    return np.asarray(im,dtype=np.float32)/255

if __name__=='__main__':
    n=4096
    s,t=np.meshgrid(np.linspace(0,1,n,dtype=np.float32),np.linspace(0,1,n,dtype=np.float32))
    coarse=noise(n,20,310);medium=noise(n,90,311);fine=noise(n,700,312)
    phase=t*165+3.2*coarse+1.5*medium+1.2*np.sin(s*12+t*18)
    wave=.5+.5*np.sin(2*np.pi*phase)
    lines=np.exp(-((wave-.18)/.095)**2)
    oxidation=smooth(.77,.94,coarse)*.24
    a,l=ornament(s,t)
    steel=np.array([.255,.276,.298],np.float32)*(1+.10*(wave[...,None]-.5))
    steel*=1-.18*lines[...,None]
    steel=steel*(1-oxidation[...,None])+np.array([.085,.068,.046],np.float32)*oxidation[...,None]
    gilt=np.array([.77,.535,.205],np.float32)*(.70+.30*l[...,None])
    color=steel*(1-a[...,None])+gilt*a[...,None]
    save('Steel','BaseColor',linear_srgb(color))
    rough=(.335+.035*lines+.028*(fine-.5)+.08*oxidation)*(1-a)+(.26+.13*(1-l))*a
    ao=1-.14*a*(1-l)
    save('Steel','ORM',np.stack([ao,rough,1-.32*oxidation],2))
    # Broad relief is geometry. This normal adds the fine scale/chisel profile
    # and micron-depth folded-steel layers, with no plastic-looking trenches.
    h=.000009*a*l+.0000011*lines+.0000003*(fine-.5)
    save('Steel','Normal',normals(h,.026/(n-1),.108/(n-1)))
    del steel,gilt,color,a,l,h,rough,ao,oxidation,phase,wave,lines
    u,v=s,1-t
    av,lv=frieze(u,(v-.03)/.43)
    ringzone=v<.50;av*=ringzone
    patina=.20*av*(1-lv)+.09*smooth(.70,.91,coarse)
    gold=np.array([.79,.555,.23],np.float32)*(1+.025*(fine[...,None]-.5))
    gold=gold*(1-patina[...,None])+np.array([.28,.135,.040],np.float32)*patina[...,None]
    # Tiny machining scratches rather than broad sine-wave 'engraving'.
    grain=.5+.5*np.sin(2*np.pi*(u*1500+.4*medium))
    save('Gilt','BaseColor',linear_srgb(gold))
    save('Gilt','ORM',np.stack([1-.12*av*(1-lv),.265+.07*patina+.026*(grain-.5),np.ones_like(u)*.98],2))
    h=.000016*av*lv+.00000024*grain+.00000012*fine
    save('Gilt','Normal',normals(h,.16/(n-1),.046/(n-1)))
    n=512
    r=noise(n,50,322)
    color=np.array([.22,.007,.010],np.float32)*(.92+.08*r[...,None])
    save('Lacquer','BaseColor',linear_srgb(color))
    save('Lacquer','ORM',np.stack([np.ones_like(r),.24+.035*r,np.zeros_like(r)],2))
    save('Lacquer','Normal',np.stack([r*0+.5,r*0+.5,r*0+1],2))
    print('YANLING_CONE_V3_PBR_AUTHORED',flush=True)
