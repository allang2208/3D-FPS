"""Bake numeric crystal orientation/tone/roughness fields, not a color illustration."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

P=Path(__file__).resolve().parent
W,H=1024,2048
# Covers the blade variants and their common root in local centimetres.
XMIN,ZMIN,XSIZE,ZSIZE=-8.,-8.,16.,128.

def noise(x,y,salt=0.):
    value=np.sin(x*127.1+y*311.7+salt)*43758.5453
    return value-np.floor(value)

def cells(x,y,salt):
    ix,iy=np.floor(x),np.floor(y)
    distance=np.full(x.shape,np.inf,dtype=np.float32)
    cellx=np.zeros_like(x);celly=np.zeros_like(y)
    for dy in (-1,0,1):
        for dx in (-1,0,1):
            nx,ny=ix+dx,iy+dy
            px=nx+.12+.76*noise(nx,ny,salt)
            py=ny+.12+.76*noise(nx,ny,salt+41.7)
            d=(px-x)**2+(py-y)**2
            win=d<distance
            distance=np.where(win,d,distance)
            cellx=np.where(win,nx,cellx);celly=np.where(win,ny,celly)
    return cellx,celly

packed=np.zeros((H,W,4),dtype=np.float32)
for begin in range(0,H,128):
    stop=min(H,begin+128)
    x,z=np.meshgrid(XMIN+(np.arange(W)+.5)*XSIZE/W,ZMIN+(np.arange(begin,stop)+.5)*ZSIZE/H)
    x=x.astype(np.float32);z=z.astype(np.float32)
    # Large, irregular domains vary the family of small finite crystal plates.
    cx,cz=cells(x/3.5,z/4.8,12.)
    family=noise(cx,cz,81.)
    angle=np.select([family<.33,family<.66],[np.deg2rad(-46),np.deg2rad(17)],np.deg2rad(63))
    angle+=(noise(cx,cz,19.)-.5)*.32
    cs,sn=np.cos(angle),np.sin(angle)
    along=x*cs+z*sn;across=-x*sn+z*cs
    # Mild spatial warping interrupts regular repeated spacing without wavy bands.
    qx=along/1.45+.10*np.sin(z*.67+x*.41)
    qy=across/.39+.12*np.sin(x*.91-z*.23)
    fx,fz=cells(qx,qy,33.)
    fine=noise(fx,fz,92.)
    direction=angle+(fine-.5)*.24
    packed[begin:stop,:,0]=.5+.5*np.cos(direction)
    packed[begin:stop,:,1]=.5+.5*np.sin(direction)
    packed[begin:stop,:,2]=.5+(noise(fx,fz,113.)-.5)*.84
    packed[begin:stop,:,3]=.5+(noise(fx,fz,177.)-.5)*.88

# Sub-pixel transition filtering prevents hard ink-like contours at plate borders.
for channel in range(4):packed[:,:,channel]=gaussian_filter(packed[:,:,channel],sigma=.65,mode='nearest')
name='T_MeteoricCrystalFieldV2.png'
Image.fromarray(np.uint8(np.clip(packed,0,1)*255+.5)).save(P/name)
(P/'field-recipe.json').write_text(json.dumps({
    'source':'procedural numeric field; no image generation',
    'size':[W,H],'local_cm_bounds':[XMIN,ZMIN,XSIZE,ZSIZE],
    'channels':{'R':'local X brush direction encoded 0..1','G':'local Z brush direction encoded 0..1',
                'B':'low-contrast crystal tone','A':'satin roughness variation'},
    'output':name,'preview_rendered':False
},indent=2)+'\n',encoding='utf8')
print('METEORIC_CRYSTAL_FIELD_AUTHORED',name)
