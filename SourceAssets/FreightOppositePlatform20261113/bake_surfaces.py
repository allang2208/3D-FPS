"""Registered colour, tangent normals and roughness from the station's mineral and fracture scans, in world cm."""
from pathlib import Path
import json,math
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates,gaussian_filter
R=Path(__file__).resolve().parent
S=R.parent/'FreightStationSurfaces20261113'
P=R.parent/'DungeonWallUpgrade20260924/Authored/Textures'
D=R.parent/'FacilityQuixel20261108/Sources/DamagedConcrete/Textures'
O=R/'Textures';O.mkdir(exist_ok=True)
def step(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3.-2.*t)
def field(rng,shape,nx,ny):
    a=rng.uniform(-1,1,(ny,nx)).astype('f')
    return np.asarray(Image.fromarray(a).resize((shape[1],shape[0]),Image.Resampling.BICUBIC))
def sample(path,U,V):
    a=np.asarray(Image.open(path).resize((896,896),Image.Resampling.LANCZOS),dtype='f')/255.
    xy=np.stack([np.mod(V,1)*895,np.mod(U,1)*895]);return np.stack([map_coordinates(c,xy,order=1,mode='wrap') for c in a.transpose(2,0,1)],axis=-1)
def emit(name,img):Image.fromarray(np.uint8(np.clip(img,0,1)*255+.5)).save(O/('T_'+name+'.png'),compress_level=2)
def distress(x,z,clusters,mid,grain):
    loss=np.zeros_like(x)
    for xc,zc,w,h,a in clusters:
        ds=np.hypot((x-xc)/w,(z-zc)/h)
        loss=np.maximum(loss,a*(1-step(.58,1.04,ds+.33*mid+.29*grain)))
    return loss
def wall(key,lo,hi,z0,z1,seed):
    shape=(1024,2048);rng=np.random.default_rng(seed)
    x,z=np.meshgrid(lo+(np.arange(2048,dtype='f')+.5)*(hi-lo)/2048,z1-(np.arange(1024,dtype='f')+.5)*(z1-z0)/1024)
    macro=field(rng,shape,8,5);mid=field(rng,shape,68,45);fine=field(rng,shape,370,238)
    streak=field(rng,shape,138,9);large=field(rng,shape,19,10);blend=step(-.72,.76,.7*macro+.42*large)
    U=x/186+.13+.016*large;V=-z/186+.37
    U2=x/112+.43;V2=-z/112+.24
    base=sample(P/'Wall_BaseColor.png',U,V)[:,:,:3].mean(2)
    other=sample(P/'Wall_BaseColor.png',U*.77+.48,V*.83+.39)[:,:,:3].mean(2)
    grit=sample(P/'FabSection_BaseColor.png',U2,V2)[:,:,:3].mean(2)
    col=.516+.79*((base*(1-blend)+other*blend)-.53)+.46*(grit-.476)+.022*macro+.012*mid+.009*streak+.012*large
    norm=sample(P/'Wall_Normal.png',U,V)[:,:,:2]*2-1
    norm=.62*norm+.57*(sample(P/'FabSection_Normal.png',U2,V2)[:,:,:2]*2-1)
    surf=sample(P/'Wall_ORM.png',U,V)
    rough=.61+.26*surf[:,:,1]+.022*mid
    # The stop end by the vertical pipe is rain-stained under its upper bend and along the last fixing.
    clusters=[(6466,621,14,28,.94),(6461,597,6,19,.81),(6475,630,10,8,.76),(6452,286,12,18,1.),(6457,266,6,10,.65),(6481,182,20,8,.82),(7013,647,8,5,.64)] if key=='Pipe' else [(-2994,185,14,23,.84),(-2979,173,7,8,.71),(-2775,166,10,4,.52)]
    loss=distress(x,z,clusters,mid,fine)
    core=sample(next(D.glob('*B-O.png')),U2*.43+.24,V2*.66+.42)[:,:,:3].mean(2)
    col=col*(1-loss)+(.38+.53*(core-.37)+.58*(grit-.48))*loss
    rim=np.maximum(gaussian_filter(loss,.9)-loss,0);col+=.21*rim
    if key=='Pipe':
        fall=np.clip((653-z)/489,0,1)
        run=np.exp(-((x-6463-3.8*mid)/(12.+8*large+8*fall))**2)*step(0,.07,fall)*(1-step(.63,1,fall))
        col-=.055*run*(.65+.35*streak);rough-=.083*run
    rough=rough*(1-loss)+(.86+.085*mid)*loss
    norm[:,:,0]+=np.clip(np.gradient(loss,axis=1),-.6,.6)*.9
    norm[:,:,1]-=np.clip(np.gradient(loss,axis=0),-.6,.6)*.9
    nn=np.dstack((norm,np.ones_like(x)));nn/=np.linalg.norm(nn,axis=2)[:,:,None]
    emit(key+'_Color',col[:,:,None]*np.array([1.023,1.005,.978],dtype='f'));emit(key+'_Normal',nn*.5+.5);emit(key+'_ORM',np.dstack((.86+.14*surf[:,:,0]-.10*loss,rough,np.zeros_like(x))))
def floor():
    W,H=2048,1024;ax,bx=6174.,7820.;ay,by=-3036.,-2010.
    x,y=np.meshgrid(ax+(np.arange(W,dtype='f')+.5)*(bx-ax)/W,ay+(np.arange(H,dtype='f')+.5)*(by-ay)/H)
    shape=x.shape;rng=np.random.default_rng(786)
    large=field(rng,shape,12,8);mid=field(rng,shape,66,40);fine=field(rng,shape,448,240)
    a=np.maximum(x-ax,0);b=np.maximum(y-ay,0)
    wall=np.minimum(a,b)
    skirt=np.exp(-wall/(23.+12*large+17*(.55+.45*mid)))+.27*np.exp(-wall/(74.+24*large))
    corner=np.exp(-((x-6460)/105)**2-((y+3025)/67)**2)
    dust=np.clip((.53*skirt+.27*corner)*(.79+.24*mid+.10*fine),0,.78)
    center=-2542+43*np.sin((x-6515)/317)+.065*(x-7000)
    lane=np.exp(-((y-center)/(117.+10*large+9*mid))**2)
    lane*=step(45,310,a)*(.85+.12*mid+.06*fine)
    # Two staggered scuff groups within the traffic path; long axis follows the walk, with irregular edges.
    scuff=np.zeros_like(x)
    for xx,yy,ang,length in [(6661,-2559,-.17,17),(6705,-2567,.18,12),(6935,-2490,-.08,22),(7204,-2542,.15,16),(7428,-2533,-.17,18),(7454,-2522,.06,9)]:
        px=x-xx;py=y-yy;d=np.hypot((px*np.cos(ang)+py*np.sin(ang))/length,(-px*np.sin(ang)+py*np.cos(ang))/2.9)
        scuff=np.maximum(scuff,.32*(1-step(.36,1.2,d+.39*fine)))
    mortar=sample(P/'Mortar_BaseColor.png',x/131,y/131)[:,:,:3].mean(2)
    dust_col=(.56+.095*mid+.068*fine+.22*(mortar-.52))[:,:,None]*np.array([1.05,.99,.88])
    lane_col=(.338+.041*large+.033*fine+.18*(mortar-.52))[:,:,None]*np.array([1.,.986,.966])
    wear=.44*lane
    soft=(1.-step(bx-130,bx,x))*(1.-step(by-85,by,y))
    total=np.maximum(.0001,dust+wear+scuff)
    rgb=(dust_col*dust[:,:,None]+lane_col*wear[:,:,None]+np.array([.24,.23,.22])*scuff[:,:,None])/total[:,:,None]
    alpha=(1-(1-dust)*(1-wear)*(1-scuff))*soft
    rough=(.97*dust+(.41+.07*mid)*wear+.46*scuff)/total
    emit('Aisle_Color',np.dstack((rgb,alpha)));emit('Aisle_Rough',rough)
def skirt(key,lo,hi):
    # Source-attributed, shallow deposits; full transparent negative space between them.
    W,H=2048,256;rng=np.random.default_rng(79 if key=='Pipe' else 31)
    x,z=np.meshgrid(lo+(np.arange(W,dtype='f')+.5)*(hi-lo)/W,158-(np.arange(H,dtype='f')+.5)*158/H)
    mid=field(rng,x.shape,110,16);fine=field(rng,x.shape,350,48);wide=field(rng,x.shape,18,4)
    if key=='Pipe':spots=[(6465,29,28,18,1),(6490,12,18,9,.86),(6438,42,14,20,.91),(6430,22,19,7,.94),(6989,10,29,6,.66),(7001,18,12,9,.75)]
    else:spots=[(-2951,24,36,16,.86),(-2970,31,20,10,.95),(-2923,16,18,7,.87),(-2432,12,26,7,.57),(-2446,17,12,4,.75)]
    chip=distress(x,z,spots,mid,fine)
    toe=np.exp(-z/(11.+4.2*wide+3*mid))*(.30+.08*mid+.05*fine)
    total=np.maximum(.001,chip+toe)
    core=sample(next(D.glob('*B-O.png')),x/47+.21,-z/47+.4)[:,:,:3].mean(2)
    color=(.41+.41*(core-.37)+.07*fine)[:,:,None]*np.array([1.05,1.0,.93])
    rgb=(color*chip[:,:,None]+np.array([.49,.455,.392])*toe[:,:,None])/total[:,:,None]
    alpha=np.clip(.81*chip+toe,0,.87)*step(lo,lo+10,x)*(1-step(hi-26,hi,x))
    # Decal U = local Z (world +Z); V = local Y (+X on the north face, -Y on the west).
    def orient(im):return np.rot90(im,-1) if key=='Pipe' else np.flip(np.rot90(im,-1),axis=0)
    emit('Toe'+key+'_Color',orient(np.dstack((rgb,alpha))));emit('Toe'+key+'_Rough',orient(np.clip(.86+.07*fine,0,1)))
if __name__=='__main__':
    wall('Return',-3036.,-1558.,159.4,1170.,381);wall('Pipe',6174.,7820.,159.4,737.,929)
    floor();skirt('Return',-3036,-1558);skirt('Pipe',6174,7820)
