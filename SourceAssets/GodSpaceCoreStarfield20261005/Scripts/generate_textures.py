"""Original seamless spherical starfield and engraved brass atlases; no concept-image pixels used."""
from pathlib import Path
import numpy as np
from scipy.ndimage import map_coordinates,gaussian_filter
from PIL import Image,ImageDraw
import json,math
ROOT=Path(__file__).resolve().parents[1] if Path(__file__).parent.name=='Scripts' else Path(__file__).parent
OUT=ROOT/'Authored/Textures';OUT.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(20261005)
W,H=4096,2048
grid=gaussian_filter(rng.random((96,96,96),dtype=np.float32),.72,mode='wrap');grid=(grid-grid.mean())/grid.std()
def noise(x,y,z,f,off=0):
    return map_coordinates(grid,[(x*f+31+off)%95,(y*f+47+off*.63)%95,(z*f+19-off*.39)%95],order=1,mode='wrap',prefilter=False)
lon=np.linspace(-np.pi,np.pi,W,dtype=np.float32)[None,:]
image=np.zeros((H,W,3),np.float32)
for start in range(0,H,128):
    end=min(H,start+128);lat=(np.pi/2-np.arange(start,end,dtype=np.float32)/(H-1)*np.pi)[:,None]
    x=np.cos(lat)*np.cos(lon);y=np.cos(lat)*np.sin(lon);z=np.broadcast_to(np.sin(lat),x.shape)
    f=(noise(x,y,z,3)*.29+noise(x,y,z,8)*.27+noise(x,y,z,19)*.23+noise(x,y,z,47)*.14+noise(x,y,z,113)*.07)
    flow=noise(x,y,z,5,11);detail=noise(x,y,z,33,21)
    plane=.55*x+.12*y+.825*z+.052*flow
    belt=np.exp(-(plane/.18)**2)
    cloud=np.clip((f+.65)/1.4,0,1)**1.05
    filaments=np.clip(.58+.45*detail,0,1)
    dust=np.clip(.78+.50*noise(x,y,z,21,43),.08,1)
    energy=belt*cloud*dust*(.34+.66*filaments)
    outer=np.clip(f+.25,0,1)*np.exp(-(plane/.38)**2)*.16
    violet=np.clip((flow+.65)/1.7,0,1)
    col=np.empty((*x.shape,3),np.float32)
    col[:]=[.009,.017,.045]
    col += (energy+outer)[...,None]*np.stack([.52+.27*violet,.67-.08*violet,.98-.04*violet],axis=-1)
    knots=np.clip((f-.30)*2.1,0,1)**1.25*belt*dust
    col += knots[...,None]*np.array([.62,.62,.72],np.float32)
    # Fine white-blue stellar filaments live only inside the tilted band.
    ridge=np.exp(-((plane-.025*detail)/.052)**2)*np.clip(noise(x,y,z,53,28)+.10,0,1)*.38
    col += ridge[...,None]*np.array([.65,.76,.9],np.float32)
    image[start:end]=col
nebula=np.clip(image.copy(),0,1);image[:]=0
def star(u,v,size,color,brightness,flare=False):
    px=u*(W-1);py=v*(H-1);coslat=max(.12,math.sin(v*math.pi));sx=size/coslat;sy=size
    radius=min(40,int(max(sx,sy)*5)+2);xx=np.arange(-radius,radius+1);yy=np.arange(-radius,radius+1)
    dx=xx[None,:]+round(px)-px;dy=yy[:,None]+round(py)-py
    profile=np.exp(-.5*((dx/sx)**2+(dy/sy)**2))
    if flare:profile+=.20*np.exp(-np.abs(dx)/(sx*4)-dy*dy/(sy*.38)**2)+.20*np.exp(-np.abs(dy)/(sy*4)-dx*dx/(sx*.38)**2)
    iy=round(py)+yy;valid=(iy>=0)&(iy<H);ix=(round(px)+xx)%W
    image[iy[valid,None],ix[None,:],:]+=profile[valid,:,None]*np.array(color)*brightness
for i in range(10500):
    zz=float(rng.uniform(-.993,.993));longitude=float(rng.uniform(-np.pi,np.pi));latitude=math.asin(zz)
    u=(longitude+np.pi)/(2*np.pi);v=(np.pi/2-latitude)/np.pi
    size=float(rng.uniform(.35,.82));bright=float(rng.uniform(.34,.95))
    color=[.72,.85,1.] if rng.random()<.79 else [1.,.86,.75]
    if i<92:size=float(rng.uniform(1.0,1.8));bright=float(rng.uniform(.9,1.5))
    star(u,v,size,color,bright,i<45)
image=np.clip(image,0,1)
image[:,0]=image[:,-1]=(image[:,0]+image[:,-1])*.5
image[0]=image[0].mean(axis=0);image[-1]=image[-1].mean(axis=0)
star_rgb=np.uint8(np.clip(image*255+.5,0,255));Image.fromarray(star_rgb).save(OUT/'T_CoreStars_Emissive.png')
nebula[:,0]=nebula[:,-1]=(nebula[:,0]+nebula[:,-1])*.5
nebula[0]=nebula[0].mean(axis=0);nebula[-1]=nebula[-1].mean(axis=0)
Image.fromarray(np.uint8(nebula*255+.5)).save(OUT/'T_CoreStarfield_BaseColor.png')
# One brass strip tile repeats eight times around each of exactly two rings.
tw,th=1024,256
engraving=Image.new('L',(tw,th),0);d=ImageDraw.Draw(engraving)
for i in range(16):
    xx=i*64+16;length=38 if i%4==0 else 24 if i%2==0 else 16
    d.line((xx,17,xx,17+length),fill=245,width=3 if i%4==0 else 2)
    d.line((xx,th-18-length,xx,th-18),fill=245,width=3 if i%4==0 else 2)
for xx in [208,720]:
    points=[]
    for j in range(8):
        angle=j*np.pi/4;rr=12 if j%2==0 else 3
        points.append((xx+rr*math.cos(angle),128+rr*math.sin(angle)))
    d.polygon(points,fill=240)
mask=np.array(engraving,dtype=np.float32)/255
yy=np.arange(th)[:,None];edge=((yy<8)|(yy>th-9)).astype(np.float32)
line=np.tile(rng.normal(0,.017,(th,1)),(1,tw));grain=rng.normal(0,.007,(th,tw))
variation=1+line+grain
color=np.clip(np.array([238,212,157])[None,None,:]*variation[...,None]*(1-mask[...,None]*.62),0,255)
rough=np.clip(.28+line*2+grain+mask*.21-edge*.14,.10,.62)
metal=np.clip(.86-mask*.13,0,1);ao=1-mask*.20
Image.fromarray(np.uint8(color)).save(OUT/'T_CoreGold_BaseColor.png')
Image.fromarray(np.uint8(np.stack([ao,rough,metal],axis=-1)*255)).save(OUT/'T_CoreGold_ORM.png')
height=gaussian_filter(-mask*.18+line*.09,sigma=.8,mode='wrap');dy,dx=np.gradient(height)
nx=-dx*3.8;ny=dy*3.8;nz=np.ones_like(nx);normal=np.stack([nx,ny,nz],axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
Image.fromarray(np.uint8((normal*.5+.5)*255)).save(OUT/'T_CoreGold_Normal.png')
report={'revision':'V2','original_procedural_art':True,'seed':20261005,'starfield_dimensions':[W,H],'seam_max_byte_delta':int(np.max(np.abs(star_rgb[:,0].astype(int)-star_rgb[:,-1].astype(int)))),'north_pole_max_channel_spread':int(np.max(np.ptp(star_rgb[0].astype(int),axis=0))),'south_pole_max_channel_spread':int(np.max(np.ptp(star_rgb[-1].astype(int),axis=0))),'star_count':10500,'independent_stars_emission':True,'ring_atlas_dimensions':[tw,th],'gold_normal_mean_z':float(normal[:,:,2].mean()),'concept_image_used_as_texture':False}
(ROOT/'Authored/texture_receipt.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
