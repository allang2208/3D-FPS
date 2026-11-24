"""Sample leather grain from the concept, tile it on the established warm brown finish."""
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

HERE=Path(__file__).resolve().parent
ART=HERE/'Art'
OUT=ART/'ReferenceLeather'
OUT.mkdir(exist_ok=True)
rgb=np.asarray(Image.open(HERE.parent/'GuardConcepts20261122/RavenQuill-Effect-V1.png').convert('RGB'),dtype='f')
lum=np.log(2+rgb@np.array([.2126,.7152,.0722],dtype='f'))
material=lum-cv2.GaussianBlur(lum,(0,0),2.4)
# Reject dark overlaps and sharp wrap seams: those are already present in the mesh.
patches=[]
for y in range(557,855,5):
    for x in range(404,465,5):
        patch=material[y:y+18,x:x+18]
        if np.percentile(lum[y:y+18,x:x+18],8)>3.14 and np.max(np.abs(patch))<.53 and patch.std()>.025:
            patches.append(patch)
rng=np.random.default_rng(2407)
n=2048
field=np.zeros((n,n),'f')
weight=np.zeros_like(field)
# Overlap feathered patches, wrapping both axes to make the grain continuous on a cylinder.
for anchor_y in range(0,n,32):
    for anchor_x in range(0,n,32):
        patch=patches[rng.integers(len(patches))]
        if rng.integers(2):patch=patch[:,::-1]
        if rng.integers(2):patch=patch[::-1]
        size=int(rng.integers(55,83))
        idx=(anchor_y+np.arange(size)-size//2+int(rng.integers(-5,5)))%n
        jdx=(anchor_x+np.arange(size)-size//2+int(rng.integers(-5,5)))%n
        w=np.outer(np.hanning(size),np.hanning(size)).astype('f')
        field[np.ix_(idx,jdx)]+=w*cv2.resize(patch,(size,size),interpolation=cv2.INTER_CUBIC)
        weight[np.ix_(idx,jdx)]+=w
field=np.clip(field/np.maximum(weight,.001),-.22,.22)
def texture(name):
    return np.asarray(Image.open(ART/('Leather_'+name+'.png')).convert('RGB'),dtype='f')
def emit(name,array):
    Image.fromarray(np.clip(array,0,255).round().astype('uint8')).save(OUT/('Leather_'+name+'.png'))
# Pigment independent of the painted scene light; slightly lighter at the worn grain tips.
colour=texture('BaseColor')+np.array([5.,3.,2.])+field[:,:,None]*np.array([47.,31.,21.])
emit('BaseColor',colour)
old=texture('Normal')/127.5-1
dx=(np.roll(field,-1,1)-np.roll(field,1,1))*.5
dy=(np.roll(field,-1,0)-np.roll(field,1,0))*.5
vec=np.stack((old[...,0]/np.maximum(.1,old[...,2])-4.2*dx,old[...,1]/np.maximum(.1,old[...,2])+4.2*dy,np.ones_like(dy)),axis=-1)
emit('Normal',(vec/np.linalg.norm(vec,axis=-1,keepdims=True)+1)*127.5)
emit('Roughness',texture('Roughness')[...,0]-field*108)
print('Authored reference leather from',len(patches),'source patches.')
