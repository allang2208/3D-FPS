"""V3 original sphere-domain nebula, independent linear stars and physical-density metal.
No reference-image pixels or V2 image resampling. Chunked generation bounds memory.
"""
from pathlib import Path
import json,math
import numpy as np
from scipy.ndimage import map_coordinates,gaussian_filter
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[1];O=R/'Authored/Textures';O.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(2026100503)
W,H=4096,2048
grid=rng.standard_normal((96,96,96),dtype=np.float32)
grid=gaussian_filter(grid,.45,mode='wrap');grid/=grid.std()
def noise(x,y,z,f,seed=0):
    return map_coordinates(grid,[(x*f+31+seed)%96,(y*f+47+seed*.63)%96,(z*f+19-seed*.39)%96],order=1,mode='grid-wrap',prefilter=False)
longitude=np.linspace(-np.pi,np.pi,W,dtype=np.float32)[None,:]
neb=np.zeros((H,W,3),np.uint8)
for first in range(0,H,48):
    last=min(H,first+48);lat=(np.pi/2-np.arange(first,last,dtype=np.float32)/(H-1)*np.pi)[:,None]
    x=np.cos(lat)*np.cos(longitude);y=np.cos(lat)*np.sin(longitude);z=np.broadcast_to(np.sin(lat),x.shape)
    flow=noise(x,y,z,5,11);plane=.55*x+.12*y+.825*z+.045*flow
    belt=np.exp(-np.square(plane/.20));halo=np.exp(-np.square(plane/.38))
    low=noise(x,y,z,3)*.25+noise(x,y,z,9,5)*.28+noise(x,y,z,23,13)*.26
    mid=noise(x,y,z,55,21)*.28+noise(x,y,z,115,33)*.24
    fine=noise(x,y,z,237,41)*.19+noise(x,y,z,491,57)*.12+noise(x,y,z,809,71)*.06
    density=np.clip(.44+low*.38+mid*.46,0,1)
    # Continuous ridged detail and narrow dust filaments, not clipped white blobs.
    ridge=np.exp(-np.abs(noise(x,y,z,94,6)+noise(x,y,z,211,8)*.36)*6)
    dust=.23+.77*np.clip(.57+noise(x,y,z,41,73)*.30+fine*.52,0,1)
    clump=np.clip(density+fine*.60,0,1)**1.6*dust
    energy=belt*(clump*.78+ridge*clump*.34)+halo*np.clip(low+.10,0,1)*.06
    violet=np.clip(.52+flow*.38,0,1)
    palette=np.stack([.17+.24*violet,.38-.18*violet,.70-.03*violet],axis=-1)
    col=np.empty((*x.shape,3),np.float32);col[:]=[.008,.014,.035]
    col+=energy[...,None]*palette*1.7
    knot=np.clip(noise(x,y,z,163,29)*.46+fine-.34,0,1)**1.3*belt*clump
    col+=knot[...,None]*np.array([.20,.36,.46],np.float32)
    col=1-np.exp(-col*1.32)
    neb[first:last]=np.uint8(np.clip(col*255+.5,0,255))
neb[:,0]=neb[:,-1]=((neb[:,0].astype(int)+neb[:,-1])/2).astype(np.uint8)
neb[0]=neb[0,0];neb[-1]=neb[-1,0]
Image.fromarray(neb).save(O/'T_CoreStarfield_BaseColor.png');del neb

stars=np.zeros((H,W),np.float32)
def star(u,v,r,amplitude,flare):
    px=u*(W-1);py=v*(H-1);sx=r/max(.035,math.sin(v*math.pi));sy=r
    rx=min(180,int(sx*4)+2);ry=int(sy*6)+2
    xx=np.arange(-rx,rx+1);yy=np.arange(-ry,ry+1)
    dx=(xx[None,:]+round(px)-px)/sx;dy=(yy[:,None]+round(py)-py)/sy
    core=np.exp(-2.3*(dx*dx+dy*dy))
    if flare:core+=.16*np.exp(-np.abs(dx)*.62-dy*dy*35)+.16*np.exp(-np.abs(dy)*.62-dx*dx*35)
    iy=round(py)+yy;valid=(iy>=0)&(iy<H);ix=(round(px)+xx)%W
    stars[iy[valid,None],ix[None,:]]+=core[valid]*amplitude
for i in range(18000):
    zz=float(rng.uniform(-.9997,.9997));u=float(rng.random());v=(np.pi/2-math.asin(zz))/np.pi
    if i<72:r=float(rng.uniform(4.8,7.2));a=float(rng.uniform(.78,1.0))
    elif i<720:r=float(rng.uniform(1.8,3.1));a=float(rng.uniform(.48,.86))
    else:r=float(rng.uniform(.52,1.0));a=float(rng.uniform(.10,.38))
    star(u,v,r,a,i<72)
stars=np.uint8(np.clip(stars*255+.5,0,255));stars[:,0]=stars[:,-1]=np.maximum(stars[:,0],stars[:,-1]);stars[0]=0;stars[-1]=0
Image.fromarray(stars).save(O/'T_CoreStars_Emissive.png');del stars

# Small three-channel periodic detail field. Triplanar sampling has no spherical poles.
n=512;detail=np.empty((n,n,3),np.float32)
for ch,sigma in enumerate([2.8,1.15,.55]):
    a=gaussian_filter(rng.standard_normal((n,n),dtype=np.float32),sigma,mode='wrap');a/=a.std()
    detail[:,:,ch]=np.clip(.5+a*.14,0,1)
Image.fromarray(np.uint8(detail*255+.5)).save(O/'T_CoreNebula_Detail.png');del detail

tw,th=2048,512
im=Image.new('L',(tw,th),0);d=ImageDraw.Draw(im)
# 4 primary sectors per tile x32 circumference repeats =128 sectors, with subdivisions.
for i in range(16):
    xx=i*128+32;length=92 if i%4==0 else 59 if i%2==0 else 32
    width=5 if i%4==0 else 3
    d.line((xx,32,xx,32+length),fill=235,width=width)
    d.line((xx,th-33-length,xx,th-33),fill=235,width=width)
for xx in [350,1374]:
    points=[]
    for j in range(8):
        a=j*np.pi/4;rr=24 if j%2==0 else 7;points.append((xx+rr*math.cos(a),th/2+rr*math.sin(a)))
    d.polygon(points,fill=255)
d.line((0,17,tw-1,17),fill=100,width=2);d.line((0,th-18,tw-1,th-18),fill=100,width=2)
mask=np.asarray(im,dtype=np.float32)/255
# Long correlated grains with shorter tooling marks; independent BC, roughness and normal.
long=gaussian_filter(rng.standard_normal((th,tw),dtype=np.float32),(.50,13),mode='wrap');long/=long.std()
short=gaussian_filter(rng.standard_normal((th,tw),dtype=np.float32),(.40,2.8),mode='wrap');short/=short.std()
grain=long*.010+short*.004
color=np.array([220,164,76],dtype=np.float32)[None,None,:]*(1+grain[...,None])*(1-mask[...,None]*.65)
rough=np.clip(.32+grain*2.5+mask*.23,.17,.70);metal=np.ones_like(mask)*.94;ao=1-mask*.22
Image.fromarray(np.uint8(np.clip(color,0,255))).save(O/'T_CoreGold_BaseColor.png')
Image.fromarray(np.uint8(np.stack([ao,rough,metal],axis=-1)*255+.5)).save(O/'T_CoreGold_ORM.png')
height=gaussian_filter(-mask*.12,sigma=.6,mode='wrap')+grain*.16
dy=(np.roll(height,-1,0)-np.roll(height,1,0))*.5;dx=(np.roll(height,-1,1)-np.roll(height,1,1))*.5
normal=np.stack([-dx*4.8,dy*3.0,np.ones_like(mask)],axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
Image.fromarray(np.uint8((normal*.5+.5)*255+.5)).save(O/'T_CoreGold_Normal.png')
def bc_mips(w,h,b):
    total=0
    while True:
        total+=((w+3)//4)*((h+3)//4)*b
        if w==1 and h==1:return total
        w=max(1,w//2);h=max(1,h//2)
old=2*bc_mips(W,H,16)+3*bc_mips(1024,256,16)
new=bc_mips(W,H,16)+bc_mips(W,H,8)+bc_mips(512,512,16)+3*bc_mips(tw,th,16)
report={'revision':'V4-cloud-refined','original_new_art':True,'old_images_resampled':False,'starfield_dimensions':[W,H],'stars_dimensions':[W,H],'stars_linear_grayscale_BC4':True,'star_count':18000,'hero_stars':72,'detail_tile':[512,512],'ring_atlas':[tw,th],'ring_u_repeats':32,'old_ring_u_repeats':8,'sphere_diameter_cm':300,'estimated_full_chain_texture_mib_before':old/2**20,'estimated_full_chain_texture_mib_after':new/2**20,'estimate_assumption':'BC7 RGB, BC4 stars, BC5 normal, conservative BC3 ORM, all mip levels resident; excludes engine bookkeeping','actual_residency_measured':False}
(R/'Authored/texture_receipt.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
