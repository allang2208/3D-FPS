"""Physical-scale cellular leather, aligned stitch sockets, forged and engraved metal."""
from pathlib import Path
import sys,json
import numpy as np
from PIL import Image,ImageFilter,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parent))
from surface import *
P=Path(__file__).resolve().parent;T=P/'Textures';T.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(20261031)
def noise(w,h,nx,ny,blur=0):
    a=rng.integers(0,256,(ny,nx),dtype=np.uint8)
    im=Image.fromarray(np.tile(a,(3,3))).resize((w*3,h*3),Image.Resampling.BICUBIC)
    if blur:im=im.filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(im.crop((w,h,2*w,2*h)),dtype=np.float32)/255-.5
def save(family,base,rough,metal,height,meters,ao):
    h,w=height.shape
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))/(2*meters[0]/w)
    # Image rows go down; the authored UV V coordinate goes up.
    dy=(np.roll(height,-1,0)-np.roll(height,1,0))/(2*meters[1]/h)
    n=np.stack((-dx,dy,np.ones_like(dx)),axis=-1);n/=np.linalg.norm(n,axis=-1,keepdims=True)
    orm=np.stack((np.broadcast_to(ao,(h,w)),rough,np.broadcast_to(metal,(h,w))),axis=-1)
    for kind,data in [('BaseColor',base),('ORM',orm),('Normal',n*.5+.5)]:
        Image.fromarray(np.uint8(np.clip(data,0,1)*255)).save(T/f'T_StaticField_{family}_{kind}.png')
    Image.fromarray(np.uint16(np.clip((height+.00015)/.0003,0,1)*65535)).save(T/f'H_StaticField_{family}_Source16.png')
    print('PBR_SAVED',family,w,h,flush=True)
# Full cylindrical atlas. A jittered cellular grain supplies irregular hide valleys,
# not large blurred clouds. There is no painted light or shadow.
W,H=4096,8192
xx=(np.arange(W,dtype=np.float32)+.5)/W*(TAU*R)
zz=Z1-(np.arange(H,dtype=np.float32)+.5)/H*(Z1-Z0)
cell=.00072;nx=int(np.ceil(TAU*R/cell));ny=int(np.ceil((Z1-Z0)/cell))+4
jx=rng.random((ny,nx),dtype=np.float32);jy=rng.random((ny,nx),dtype=np.float32)
height=np.empty((H,W),dtype=np.float32);grain=np.empty_like(height)
for row in range(0,H,256):
    zv=(Z1-zz[row:row+256,None])/cell+1; xv=xx[None,:]/(TAU*R)*nx
    ix=np.floor(xv).astype(int);iy=np.floor(zv).astype(int);d1=np.full((len(zv),W),100,dtype=np.float32);d2=d1.copy()
    for oz in (-1,0,1):
        for ox in (-1,0,1):
            gx=ix+ox;gz=iy+oz;dx=xv-(gx+jx[gz%ny,gx%nx]);dz=zv-(gz+jy[gz%ny,gx%nx])
            d=dx*dx+dz*dz;new=np.minimum(d1,d);d2=np.minimum(d2,np.maximum(d1,d));d1=new
    valley=np.exp(-((np.sqrt(d2)-np.sqrt(d1))/.085)**2)
    pebble=1-np.clip(np.sqrt(d1),0,1)
    grain[row:row+len(zv)]=valley
    height[row:row+len(zv)]=pebble*.000013-valley*.000017
fine=noise(W,H,1500,2800,.35);cloud=noise(W,H,36,130,3)
height+=fine*.000003
# Needle sockets and pressed edges share the exact stitch coordinates used by author.py.
a=(np.arange(W,dtype=np.float32)+.5)/W*TAU
s=seam(a[None,:],zz[:,None]);d=conduct(a[None,:],zz[:,None])
pressure=np.exp(-((s-.00105)/.00060)**2)
holes=Image.new('L',(W,H));hd=ImageDraw.Draw(holes)
for i in range(440):
    z=Z0+.001+(Z1-Z0-.002)*i/439;aa=TAU*(z-Z0)/PITCH+.2-.26
    for t in (-.5,.5):
        u=((aa+t*.069)%TAU)/TAU*W;v=(Z1-z-t*.0012)/(Z1-Z0)*H
        for offset in (-W,0,W):hd.ellipse((u+offset-4,v-2,u+offset+4,v+2),fill=255)
pores=np.asarray(holes.filter(ImageFilter.GaussianBlur(1.2)),dtype=np.float32)/255
height-=pores*.000035
wear=np.exp(-((s-.00085)/.00043)**2)
base=np.array([.205,.120,.067],dtype=np.float32)[None,None,:]*(1+cloud[:,:,None]*.20-grain[:,:,None]*.15+wear[:,:,None]*.22)
base*=1-.38*np.exp(-(s/.00045)**2)[:,:,None]
rough=np.clip(.64+cloud*.10+grain*.10-pressure*.10-wear*.07,0,1)
save('Leather',base,rough,0,height,(TAU*R,Z1-Z0),1-.12*grain-.12*pores)
del height,grain,fine,cloud,s,d,pressure,pores,wear,base,rough
for family,metal,basecolor in [('Steel',.95,[.26,.27,.28]),('Silver',.98,[.64,.62,.57])]:
    W=H=4096
    hammer=noise(W,H,260,260,1);fine=noise(W,H,1400,1400,.3);cloud=noise(W,H,55,55,2)
    sc=Image.new('L',(W,H));dr=ImageDraw.Draw(sc)
    for i in range(2300):
        x=int(rng.integers(W));y=int(rng.integers(H));length=int(rng.integers(8,110))
        dr.line((x,y,x+int(rng.integers(-8,9)),y+length),fill=int(rng.integers(30,160)),width=1)
    scratches=np.asarray(sc.filter(ImageFilter.GaussianBlur(.6)),dtype=np.float32)/255
    height=hammer*(.000004 if family=='Steel' else .0000012)+fine*.0000007-scratches*.000003
    rough=np.clip((.53 if family=='Steel' else .37)+cloud*.10+hammer*.025+scratches*.12,0,1)
    base=np.array(basecolor,dtype=np.float32)[None,None,:]*(1+cloud[:,:,None]*.09-scratches[:,:,None]*.05)
    save(family,base,rough,metal,height,(.065,.065),1-scratches*.06)
    del hammer,fine,cloud,scratches,height,rough,base
(P/'texture_manifest.json').write_text(json.dumps(dict(normal='OpenGL tangent-space; UE flip green',leather=dict(size=[4096,8192],uv='circumference and full contact length',physical_m=[float(TAU*R),Z1-Z0]),metal=dict(size=[4096,4096],physical_tile_m=.065),microheight='cellular hide, needle sockets, forged grain and directional scratches; macro folds are real geometry'),indent=2),encoding='utf-8')
