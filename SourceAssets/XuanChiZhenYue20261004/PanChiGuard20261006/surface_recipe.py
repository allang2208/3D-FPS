"""Bake sculpt parameters and copper PBR from the commissioned wing height field."""
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, distance_transform_edt, binary_opening, label
P=Path(__file__).resolve().parent
W,H=.148,.057

def artwork(size):
    im=Image.open(P/'Ornament/Wing_HeightSource.png').convert('RGBA')
    box=im.getchannel('A').point(lambda v:255 if v>180 else 0).getbbox()
    if box is None:raise RuntimeError('Sculpt source has no solid wing silhouette')
    im=im.crop(box).resize(size,Image.Resampling.LANCZOS)
    rgba=np.asarray(im,dtype=np.float32)/255.
    mask=binary_opening(rgba[:,:,3]>.68,iterations=1)
    regions,n=label(mask)
    counts=np.bincount(regions.ravel());counts[0]=0
    mask=regions==counts.argmax()
    lum=np.sum(rgba[:,:,:3]*[.2126,.7152,.0722],axis=2)
    return lum,mask

def height(lum):
    return .0032*np.clip((lum-.22)/.66,0,1)**1.25

def srgb(a):
    return np.where(a<=.0031308,12.92*a,1.055*np.maximum(a,0)**(1/2.4)-.055)

def bake():
    lum,mask=artwork((321,125))
    dist=distance_transform_edt(mask,sampling=(H/124,W/320))
    sculpt=height(gaussian_filter(lum,.62))
    np.savez_compressed(P/'Ornament/wing_geometry.npz',height=sculpt,mask=mask,distance=dist)
    # Single 2K atlas shared by both mirrored wings and both faces.
    nx,ny=2048,1024;x0,x1=40,1884;y0,y1=40,984
    lum,mask=artwork((x1-x0,y1-y0));relief=height(lum)
    rng=np.random.default_rng(20261006)
    grain=rng.normal(0,.008,lum.shape).astype(np.float32)
    raised=np.clip((lum-.28)/.40,0,1);raised=raised*raised*(3-2*raised)
    copper=np.array([.73,.337,.153]);recess=np.array([.078,.039,.021])
    linear=(recess[None,None,:]*(1-raised[:,:,None])+copper[None,None,:]*raised[:,:,None])
    linear*=np.clip(1.+grain,.96,1.04)[:,:,None]
    color=np.empty((ny,nx,3),np.uint8);color[:]=np.clip(srgb(copper*.68)*255,0,255)
    orm=np.empty_like(color);orm[:]=[242,91,250]
    normal=np.empty_like(color);normal[:]=[128,128,255]
    color[y0:y1,x0:x1]=np.clip(srgb(linear)*255,0,255)
    orm[y0:y1,x0:x1]=np.stack([.77+.22*raised,.47-.20*raised+grain,.96+.035*raised],2)*255
    # Geometry takes the broad relief; the normal map supplies fine scale/chisel detail.
    micro=np.clip(relief-gaussian_filter(relief,3.5),-.00020,.00020)*.44+grain*.000035
    dy,dx=np.gradient(micro,H/(y1-y0-1),W/(x1-x0-1))
    nn=np.stack([-dx,dy,np.ones_like(dx)],2);nn/=np.linalg.norm(nn,axis=2)[:,:,None]
    normal[y0:y1,x0:x1]=np.clip((nn*.5+.5)*255,0,255)
    for key,a in [('BaseColor',color),('ORM',orm),('Normal',normal)]:
        Image.fromarray(a).save(P/'Textures'/('PanChi_'+key+'.png'))
    Image.fromarray((np.clip(relief/.0032,0,1)*65535).astype(np.uint16)).save(P/'Textures/PanChi_Height16.png')
    print('PANCHI_COPPER_PBR_AUTHORED',flush=True)

if __name__=='__main__':bake()
