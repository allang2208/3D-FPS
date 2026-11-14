"""Masks in surveyed world centimetres. R joints, G wheel rubber, B dust, A slab patina."""
from pathlib import Path
from PIL import Image
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.spatial import cKDTree
root=Path(__file__).resolve().parent
N=1536
rng=np.random.default_rng(75031)
def field(n):
    data=rng.random((n,n),dtype=np.float32)
    return np.asarray(Image.fromarray(data).resize((N,N),Image.Resampling.BICUBIC)).clip(0,1)
def save(name,*channels):
    Image.fromarray(np.uint8(255*np.stack(channels,axis=-1).clip(0,1))).save(root/(name+'.png'))
def smooth(a,b,v):
    t=np.clip((v-a)/(b-a),0,1);return t*t*(3-2*t)
def coords(origin,span):
    return origin+(np.arange(N,dtype=np.float32)+.5)*span/N
x,y=np.meshgrid(coords(8317,400),coords(-600,400))
pore,mottle,wave=field(537),field(34),field(8)
envelope=smooth(0,12,x-8317)*smooth(0,12,8717-x)*smooth(0,15,y+600)*smooth(0,14,-200-y)
# Follow the two rows of bevel vertices already present in the platform mesh.
def gap(v,origin,pitch):
    return abs((v-origin+pitch*.5)%pitch-pitch*.5)
joint=np.minimum(gap(x,8499.06,117.1875),gap(y,-355.77,86.53846))
width=.25+.42*mottle+.22*pore
seam=(1-smooth(width,width+.38,joint))*(.72+.25*pore)
line_chips=(1-smooth(.5,2.6,joint))*smooth(.76,.95,mottle)*(.4+.35*pore)
seam=np.maximum(seam,line_chips)
# Wheel axles run along X. The paired tyre centres are 82 cm apart and each tyre is 4 cm wide.
s=np.linspace(0,1,720)
curve=np.stack([PchipInterpolator([0,.2,.6,1],v)(s) for v in ([8428,8435,8506,8648],[-334,-404,-493,-589])],axis=1)
tangent=np.gradient(curve,axis=0);tangent/=np.linalg.norm(tangent,axis=1)[:,None]
normal=np.stack([-tangent[:,1],tangent[:,0]],axis=1)
samples=np.stack([x,y],axis=-1).reshape(-1,2)
rubber=np.zeros_like(x)
for side in (-1,1):
    dist,index=cKDTree(curve+side*41*normal).query(samples,workers=4)
    dist,index=dist.reshape(x.shape),index.reshape(x.shape)
    travel=s[index];w=1.68+.56*mottle
    core=(1-smooth(.60*w,1.32*w,dist))
    shoulder=np.exp(-((dist-1.29)/.40)**2)
    contact=(.42+.58*smooth(.19,.68,mottle))*(.55+.45*pore)
    fade=smooth(.0,.055,travel)*(1-smooth(.94,1,travel))
    interruption=.22+.78*smooth(-.85,.10,np.sin(travel*26+side*2.1)+.85*wave)
    rubber=np.maximum(rubber,(core*.70+shoulder*.30)*contact*fade*interruption)
wallfoot=np.exp(-((x-8318)/(11+19*wave))**2)
under=np.exp(-((x-8425)/74)**2-((y+307)/47)**2)
dust=(wallfoot*.84+under*.32+.22*np.exp(-joint/3.1))*(.23+.54*mottle+.23*pore)
dust*=1-.7*rubber
i=np.floor((x-8499.06)/117.1875);j=np.floor((y+355.77)/86.53846)
panel=np.mod(np.sin(i*41.113+j*17.17)*713.57,1)
save('T_CartBayFloorMasks',seam*envelope,rubber*envelope,dust*envelope,(.12+.50*panel+.28*wave+.10*mottle)*envelope)
# Wall-space axes are along the facade and vertical. Drips start at specific coping joints.
y,z=np.meshgrid(coords(-548,432),coords(0,236))
grain,smear,broad=field(480),field(32),field(8)
edge=smooth(0,12,y+548)*smooth(0,12,-116-y)*(1-smooth(199,236,z))
drips=np.zeros_like(z)
for yy,top,length,width in [(-402,89,58,3.7),(-399,86,80,1.4),(-265,89,72,3.0),(-262,88,47,1.3),(-469,192,98,3.4),(-467,185,112,.92),(-205,162,87,2.2),(-199,160,57,1.1)]:
    fall=(top-z)/length
    path=yy+.74*np.sin(fall*7+yy)+.92*(smear-.5)
    line=np.exp(-((y-path)/(width*(1-.52*np.clip(fall,0,1))+.34))**2)
    halo=np.exp(-((y-path)/(width*2.1+1))**2)*.24
    drips=np.maximum(drips,(line+.36*halo)*smooth(-.03,.045,fall)*(1-smooth(.66,1,fall))*(.44+.4*smear+.16*grain))
toe=np.exp(-(z/(8+13*broad))**1.3)*(.45+.39*smear+.16*grain)
veil=(.25+.47*smear+.28*broad)*(.77+.23*grain)
save('T_CartBayWallMasks',drips*edge,toe*edge,veil*edge,edge)
