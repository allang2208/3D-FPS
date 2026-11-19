"""Tileable, uneven hand-spun flax with alternating over/under crossings."""
from pathlib import Path
import numpy as np
from PIL import Image

dest=Path(__file__).resolve().parents[4]/'SourceAssets/HillsVillageTavern/KitchenStations'
dest.mkdir(exist_ok=True,parents=True)
size=512
y,x=np.mgrid[:size,:size]/size
tau=2*np.pi
rng=np.random.default_rng(46238)
u=48*x+.15*np.sin(tau*(2*y+x))+.065*np.sin(tau*(3*x-8*y))
v=46*y+.14*np.sin(tau*(4*x-y))+.075*np.sin(tau*(9*x+2*y))
warp=np.maximum(0,1-np.abs(np.sin(np.pi*u))**3.4)
weft=np.maximum(0,1-np.abs(np.sin(np.pi*v))**3.6)
mask=.5+.5*np.cos(np.pi*u)*np.cos(np.pi*v)
fiber=warp*mask+weft*(1-mask)
slub=.5*np.sin(tau*(5*x+y))+.3*np.sin(tau*(2*x-4*y))+.2*np.cos(tau*(3*x+2*y))
fleck=rng.normal(0,.015,(size,size))
stripe=np.exp(-(np.sin(np.pi*(y-.12))/.037)**2)+.63*np.exp(-(np.sin(np.pi*(y-.155))/.023)**2)
color=(.70+.25*fiber+.065*slub+fleck)[:,:,None]*np.array([165,148,119])[None,None,:]
color-=stripe[:,:,None]*np.array([46,24,9])[None,None,:]
height=.68*fiber+.2*warp+.14*weft+.4*fleck
dx=(np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))*.58
dy=(np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))*.58
norm=np.sqrt(1+dx*dx+dy*dy)
normal=np.stack([.5-.5*dx/norm,.5-.5*dy/norm,.5+.5/norm],axis=-1)
rough=np.clip(.89-.07*fiber+.025*slub+fleck,0,1)
for suffix,arr in (('Color',color),('Normal',normal*255),('Rough',rough*255)):
    Image.fromarray(np.uint8(np.clip(arr,0,255))).save(dest/('T_KitchenLinen_'+suffix+'.png'))
