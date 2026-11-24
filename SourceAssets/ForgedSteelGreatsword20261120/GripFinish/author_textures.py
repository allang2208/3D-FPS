"""Bake periodic full-colour grip finishes in sRGB with matching OpenGL normal and roughness maps."""
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

ART=Path(__file__).resolve().parent/'Art'
N=2048
rng=np.random.default_rng(221122)
y,x=np.mgrid[:N,:N].astype(np.float32)
u,v=x/N,y/N
def noise(cells):
    grid=rng.normal(0,1,(cells,cells)).astype(np.float32)
    return cv2.remap(grid,u*cells,v*cells,cv2.INTER_CUBIC,borderMode=cv2.BORDER_WRAP)
broad=noise(9)*.65+noise(21)*.35
grain=noise(315)*.6+noise(680)*.4
def emit(name,colour,height,rough):
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))*.5
    dy=(np.roll(height,-1,0)-np.roll(height,1,0))*.5
    normal=np.stack((-dx,dy,np.ones_like(dx)),axis=-1)
    normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    for tag,array in [('BaseColor',colour),('Normal',127.5*(normal+1)),('Roughness',255*rough)]:
        Image.fromarray(np.uint8(np.clip(array,0,255))).save(ART/(name+'_'+tag+'.png'))

# Oil-darkened valleys and warmer worn grain tops, continuous across the wrap UV seam.
seeds=rng.uniform(0,N,(51000,2))
tree=cKDTree(seeds,boxsize=N)
creases=np.empty((N,N),np.float32)
for a in range(0,N,128):
    sample=np.stack((x[a:a+128],y[a:a+128]),axis=-1)
    dist,_=tree.query(sample,k=2)
    creases[a:a+128]=np.exp(-((dist[...,1]-dist[...,0])/1.25)**2)
crease=cv2.GaussianBlur(creases,(3,3),.38)
wear=.45*broad+.30*noise(67)+.15*grain-.70*crease
leather=np.array([83.,45.,29.])+wear[:,:,None]*np.array([16.,11.,7.])
emit('Leather',leather,.29*grain-.95*crease+.10*noise(73),.55-.080*np.tanh(wear)+.07*crease)
# Alternating warp and weft with a finer twisted fibre inside each yarn.
frequency=112
warp=.5+.5*np.cos(2*np.pi*u*frequency)
weft=.5+.5*np.cos(2*np.pi*v*frequency)
over=(np.cos(np.pi*frequency*u)*np.cos(np.pi*frequency*v)>0)
relief=np.where(over,warp+.19*weft,weft+.19*warp)
filaments=np.sin(2*np.pi*(u+v)*384)
fabric=np.array([52.,43.,40.])+ (12*(relief-.55)+4*broad+1.9*filaments)[:,:,None]
emit('Textile',fabric,1.45*relief+.14*filaments+.08*grain,.78-.09*relief+.025*broad)
# Brushed, aged steel fittings with a restrained warm tone.
brush=noise(75)*.27+np.cos(2*np.pi*v*530+.45*np.sin(2*np.pi*u*4))*.27+grain*.16
steel=np.array([124.,112.,99.])+(5.6*broad+5.3*brush)[:,:,None]
emit('Steel',steel,.43*brush,.38+.037*broad+.030*brush)
