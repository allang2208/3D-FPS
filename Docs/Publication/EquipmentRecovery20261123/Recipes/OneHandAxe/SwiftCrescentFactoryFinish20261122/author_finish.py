"""Lay the factory head's actual PBR artwork onto the approved Crescent UV islands."""
from pathlib import Path
import json
import os
import cv2
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

art = Path(__file__).resolve().parent
batch = Path(os.environ['CRESCENT_BATCH'])
source = Path(os.environ['FPSGAME_PROJECT'])/'SourceAssets/OneHandAxe20261101'
recipe = json.loads((source/'BladeVariants20261102/CrescentReferenceR4_20261104/FactoryFinish20261104/texture_recipe.json').read_text('utf8'))
fields = np.load(art/'finish-fields.npz')
atlas_size = 4096
scale = float(fields['scale'])
roles = ('BaseColor','ORM','Normal')

def linear(rgb):
    return np.where(rgb <= .04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
def srgb(rgb):
    return np.where(rgb <= .0031308,rgb*12.92,1.055*np.maximum(rgb,0)**(1/2.4)-.055)
def normalized(v):
    return v / np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1.e-8)
def texture(image,u,v,periodic=False):
    return cv2.remap(image,u.astype('f4'),v.astype('f4'),cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_WRAP if periodic else cv2.BORDER_REPLICATE)
def sampling_frame(u,v,size):
    # Three overlapping samples share the same offsets across all PBR channels.
    # Keep the brushed silver's grain direction, but avoid repeating the same scuff.
    u=u/size[0]
    v=v/size[1]
    gx=u*.92-v*.36
    gy=v*1.07+u*.21
    ix=np.floor(gx).astype('i4')
    iy=np.floor(gy).astype('i4')
    fx=gx-ix
    fy=gy-iy
    upper=fx+fy>1
    vertices=((ix+upper,iy+upper,np.abs(1-fx-fy)),
              (ix+1,iy,np.where(upper,1-fy,fx)),
              (ix,iy+1,np.where(upper,1-fx,fy)))
    samples=[]
    norm=np.zeros_like(u)
    for x,y,w in vertices:
        seed=x.astype(np.int64)*198491317+y.astype(np.int64)*6542989
        def offset(k):
            z=(seed+k) & 0xffffffff
            z=((z^(z>>16))*0x45d9f3b) & 0xffffffff
            return (((z^(z>>16)) & 0xffff)/65536).astype('f4')
        weight=(w*w*(3-2*w)).astype('f4')
        norm+=weight
        samples.append((np.mod(u+offset(1099),1),np.mod(-v+offset(8071),1),weight))
    return [(s,t,(w/norm)[:,:,None]) for s,t,w in samples]

def swatch_sample(tile,coordinates):
    h,w=tile.shape[:2]
    return sum(texture(tile,s*w,t*h,True)*weight for s,t,weight in coordinates)

def swatch(path,box,role,body):
    with Image.open(path) as im:
        rgb=np.asarray(im.crop(tuple(box)).convert('RGB'),dtype=np.float32)/255
    if role=='BaseColor': rgb=linear(rgb)
    # The scan contains both micrograin and broad lighting/wear blotches.
    # Carry the measured factory mean and fine grain, subdue broad mottling.
    mean=rgb.mean(axis=(0,1),keepdims=True)
    broad=cv2.GaussianBlur(rgb,(0,0),9. if body else 4.)
    rgb=mean+(broad-mean)*(.22 if body else .45)+(rgb-broad)*(.92 if body else 1.)
    if role=='Normal':
        rgb[:,:,:2]-=mean[:,:,:2]-.5
    # Match the factory transfer recipe at periodic borders; keep the channels registered.
    h,w=rgb.shape[:2]
    band=max(2,min(w,h)//8)
    for i in range(band):
        weight=.5*(1-i/band)**2
        a,b=rgb[:,i].copy(),rgb[:,w-1-i].copy()
        rgb[:,i],rgb[:,w-1-i]=a*(1-weight)+b*weight,b*(1-weight)+a*weight
        a,b=rgb[i].copy(),rgb[h-1-i].copy()
        rgb[i],rgb[h-1-i]=a*(1-weight)+b*weight,b*(1-weight)+a*weight
    return rgb

tiles={region:{role:swatch(batch/'Factory'/(role+'.tga'),spec['swatch_pixels'],role,region=='body')
               for role in roles} for region,spec in recipe['regions'].items()}
sizes={key:spec['swatch_physical_m'] for key,spec in recipe['regions'].items()}
edge_curve=fields['outer']
# Express the original brushed edge swatch in distance along and across the curved border.
world_curve=np.stack((float(fields['cx'])+(550-edge_curve[:,0])*scale,
                      float(fields['base_z'])+(940-edge_curve[:,1])*scale),axis=-1)
seg=np.diff(world_curve,axis=0);length=np.linalg.norm(seg,axis=1)
arc=np.r_[0,np.cumsum(length)]
y0,x0=np.mgrid[:1024,:1024].astype('f4')
world=np.stack((float(fields['cx'])+(550-x0)*scale,float(fields['base_z'])+(940-y0)*scale),axis=-1)
idx=cKDTree((world_curve[1:]+world_curve[:-1])*.5).query(world,workers=4)[1]
t=normalized(seg[idx])
across=np.stack((t[:,:,1],-t[:,:,0]),axis=-1)
offset=world-world_curve[idx]
travel=np.clip(np.sum(offset*t,axis=-1),0,length[idx])
edge_frame=np.stack((np.sum(offset*across,axis=-1),arc[idx]+travel,t[:,:,0],t[:,:,1]),axis=-1).astype('f4')
silver=fields['silver']
ring=fields['ring_xy']
perimeter=float(fields['perimeter_m'])
ys,xs=np.gradient(cv2.GaussianBlur(fields['front_field'],(0,0),2.2))
front_grad=np.stack((xs,ys),axis=-1)
ys,xs=np.gradient(cv2.GaussianBlur(fields['back_field'],(0,0),2.2))
back_grad=np.stack((xs,ys),axis=-1)

def tangent_axis(n,x,z):
    axis=np.stack((x,np.zeros_like(x),z),axis=-1)
    return normalized(axis-n*np.sum(n*axis,axis=-1,keepdims=True))
def projected_normal(tex,n,axis,bitangent):
    local=tex*2-1
    return axis*local[:,:,:1]+bitangent*local[:,:,1:2]+n*local[:,:,2:3]
def orient_v(n,axis,x,z):
    b=np.cross(n,axis)
    return b*np.where(b[:,:,0]*x+b[:,:,2]*z<0,-1,1)[:,:,None]

images={k:Image.new('RGB',(atlas_size,atlas_size)) for k in roles}
columns=(np.arange(atlas_size,dtype='f4')+.5)/atlas_size
# The two cheek islands are mirrored. The independent middle strip follows the
# perimeter and supplies physical-scale detail on the back and the inside curve.
for row in range(0,atlas_size,64):
    u,v=np.meshgrid(columns,(np.arange(row,row+64,dtype='f4')+.5)/atlas_size)
    y=v*1024; x=np.minimum(u,1-u)*2048
    reverse=u>.5
    strip=(u>.42)&(u<.58)
    s=np.clip((1-v-.015)/.97,0,1)
    curve_index=s*(len(ring)-1)
    rx=np.interp(curve_index,np.arange(len(ring)),ring[:,0]).astype('f4')
    ry=np.interp(curve_index,np.arange(len(ring)),ring[:,1]).astype('f4')
    x=np.where(strip,rx,x)
    y=np.where(strip,ry,y)
    wx=float(fields['cx'])+(550-x)*scale
    wz=float(fields['base_z'])+(940-y)*scale
    bu=np.where(strip,(u-.5)*2048*scale,wx)
    bv=np.where(strip,s*perimeter,wz)
    frame=texture(edge_frame,x,y)
    eu=np.where(strip,bu,frame[:,:,0])
    ev=np.where(strip,bv,frame[:,:,1])
    weight=texture(silver,x,y)[:,:,None]
    grad=np.where(reverse[:,:,None],texture(back_grad,x,y),texture(front_grad,x,y))
    side=np.where(reverse,-1.,1.).astype('f4')
    n=normalized(np.stack((grad[:,:,0],side,grad[:,:,1]),axis=-1))
    one=np.ones_like(x); zero=np.zeros_like(x)
    # True UV tangents for the two deformed cheek faces.
    uv_t=normalized(np.stack((-side,grad[:,:,0],zero),axis=-1))
    uv_b=orient_v(n,uv_t,zero,one)
    body_t=tangent_axis(n,one,zero); body_b=orient_v(n,body_t,zero,one)
    ex,ez=frame[:,:,3],-frame[:,:,2]
    edge_t=tangent_axis(n,ex,ez); edge_b=orient_v(n,edge_t,frame[:,:,2],frame[:,:,3])
    body_coords=sampling_frame(bu,bv,sizes['body'])
    edge_coords=sampling_frame(eu,ev,sizes['edge'])
    for role in roles:
        body=swatch_sample(tiles['body'][role],body_coords)
        edge=swatch_sample(tiles['edge'][role],edge_coords)
        if role=='Normal':
            body_n=projected_normal(body,n,body_t,body_b)
            edge_n=projected_normal(edge,n,edge_t,edge_b)
            result=normalized(body_n*(1-weight)+edge_n*weight)
            dot=lambda vec:np.sum(result*vec,axis=-1)
            local=np.stack((dot(uv_t),dot(uv_b),dot(n)),axis=-1)
            strip_normal=normalized((body*2-1)*(1-weight)+(edge*2-1)*weight)
            pixels=np.where(strip[:,:,None],strip_normal,local)*.5+.5
        else:
            pixels=body*(1-weight)+edge*weight
            if role=='BaseColor':pixels=srgb(pixels)
        images[role].paste(Image.fromarray(np.uint8(np.clip(pixels,0,1)*255+.5)),(0,row))
for role,im in images.items(): im.save(art/'Textures'/('T_SwiftCrescent_Leaf_'+role+'.png'))
receipt={'bindings':json.loads((batch/'factory-bindings.json').read_text()),'regions':recipe['regions'],
         'atlas_size':atlas_size,'normal_encoding':'OpenGL, single green-channel conversion at UE import',
         'sampling':'shared stochastic offsets on all PBR channels, frequency-separated finish',
         'shoulder_leaves':1,'rim_uv':'dedicated middle strip','runtime_tested':False}
(art/'factory-finish.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
