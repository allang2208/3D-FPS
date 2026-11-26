"""Prepare metrically scaled road scans and deterministic, road-aligned crop locations."""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates
from scipy.spatial import cKDTree

from prepare_gate_road_surface import ORIGIN, smooth

SCANS = (
    ('b41e367e-4d65-4024-bd2d-70a004349f2b', 'sbhjy2p0', .39),
    ('0b97cb8c-d222-4ae4-9bbb-fc79ea810eb1', 'sbhjzfp0', .39),
    ('da6819a6-bffe-400e-85d8-9cba43e29fa7', 'vl0iad3g', 2.7),
)
WIDTH, HEIGHT, STEP = 2048, 512, .3125
SEED = 438719

def channels(folder, key, size, soil, reference_y):
    meta=json.loads((folder/(key+'.json')).read_text(encoding='utf-8-sig'))
    def load(channel,mode):
        file,=folder.glob('*_4K_'+channel+'.jpg')
        with Image.open(file) as im:return im.convert(mode)
    def resize(im):return im.resize((size,size),Image.Resampling.LANCZOS) if im.size!=(size,size) else im
    color=resize(load('BaseColor','RGB'))
    lum=float(np.asarray(color.resize((64,64)).convert('L')).mean())
    gain=float(np.clip(reference_y/max(lum,1.),.85,1.18))
    color=color.point(lambda x:min(255,round(x*gain)))
    normal=load('Normal','RGB')
    # Generic texture-set exports may use either Y convention. Match UE's road scans.
    n=np.asarray(normal.resize((512,512),Image.Resampling.BOX),np.float32)-127.5
    bump=np.asarray(load('Bump','L').resize((512,512),Image.Resampling.BOX),np.float32)
    dy,dx=np.gradient(bump)
    corr_x=float(np.mean(n[:,:,0]*dx));corr_y=float(np.mean(n[:,:,1]*dy))
    if corr_x>=0 or abs(corr_y)<.05:raise ValueError((key,'normal orientation',corr_x,corr_y))
    if corr_y>0:
        red,green,blue=normal.split()
        normal=Image.merge('RGB',(red,green.point(lambda x:255-x),blue))
    normal=resize(normal)
    data=Image.merge('RGB',tuple(resize(load(ch,'L')) for ch in ('AO','Roughness','Displacement')))
    ims=[color,normal,data]
    if soil:ims=[Image.fromarray(np.pad(np.asarray(im),((32,32),(32,32),(0,0)),mode='wrap')) for im in ims]
    physical_size=meta.get('physicalSize') or next(m['value'] for m in meta['meta'] if m['key']=='scanArea')
    return ims,dict(scan=key,physical_size=physical_size,output_texels=size,luma_gain=gain,green_flipped=corr_y>0)

def palettes(src,base):
    with Image.open(base/'Village/ChapelEarth_B.tga') as im:target=float(np.asarray(im.convert('L').resize((64,64))).mean())
    atlas=[Image.new('RGB',(4096,2048)) for _ in range(3)]
    meta=[]
    for i,(uid,key,meters) in enumerate(SCANS):
        ims,desc=channels(src/'Fab'/uid,key,1984 if i<2 else 4096,i<2,target)
        desc.update(listing=uid,meters=meters);meta.append(desc)
        for j,suffix in enumerate(('Color','Normal','ARH')):
            if i<2:atlas[j].paste(ims[j],(2048*i,0))
            else:ims[j].save(src/('T_Tire'+suffix+'.png'))
    for suffix,im in zip(('Color','Normal','ARH'),atlas):im.save(src/('T_Stony'+suffix+'.png'))
    return meta

def placement(src,terrain):
    rng=np.random.default_rng(SEED)
    yy,xx=np.indices((HEIGHT,WIDTH),dtype=np.float32)
    x=ORIGIN[0]+(xx+.5)*STEP;y=ORIGIN[1]+(yy+.5)*STEP
    def noise(m):
        grid=rng.normal(size=(math.ceil(HEIGHT*STEP/m)+4,math.ceil(WIDTH*STEP/m)+4))
        return np.tanh(map_coordinates(grid,[1+yy*STEP/m,1+xx*STEP/m],order=3,mode='nearest'))
    slow,patch,edge=noise(17.),noise(4.1),noise(1.35)
    hill=json.loads((terrain/'hill.json').read_text());cx,cy=hill['village_center_m']
    layout=Path(__file__).resolve().parents[3]/'SourceAssets/TemperateHillsVillage/layout.json'
    ex,ey=json.loads(layout.read_text(encoding='utf-8-sig'))['surface_extent_m']
    lx,ly=np.abs(cy-y),np.abs(x-cx)
    exterior=smooth(.20,2.45,np.maximum.reduce([lx-ex,ly-ey,(lx+ly-ex-ey+6.)*.70710678]))
    for file,n,step,threshold in ((terrain/'quarry-clear.u8',1025,1.,(.18,.85)),(terrain/'Grass/pond_wet.u8',4097,.25,(.02,.38))):
        grid=np.memmap(file,dtype='u1',mode='r',shape=(n,n))
        protected=map_coordinates(grid,[(y+320)/step,(x+624)/step],order=1,prefilter=False,mode='nearest')/255.
        exterior*=1.-smooth(*threshold,protected)
    points=np.column_stack((x.ravel(),y.ravel()))
    lane=np.zeros_like(x);stone=np.zeros_like(x);coarse=np.zeros_like(x)
    ids=np.zeros((HEIGHT,WIDTH),dtype='u1');lut=np.zeros((4,256,4),dtype='u1');stamps=[]
    for name in ('gate','quarry'):
        line=np.loadtxt(terrain/(name+'-road.csv'),delimiter=',',skiprows=1)[:,:2]
        if name=='gate':line=line[::-1]
        dist,idx=cKDTree(line).query(points);dist=dist.reshape(x.shape);idx=idx.reshape(x.shape)
        chain=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(line,axis=0),axis=1))]
        quarry=smooth(chain[-1]-80.,chain[-1]-8.,chain[idx]) if name=='quarry' else 0.
        band=1.-smooth(3.5+.28*edge,5.3+.34*patch,dist)
        lane=np.maximum(lane,band)
        stone=np.maximum(stone,band*np.clip(.44+.16*slow+.17*patch+.09*smooth(.8,3.4,dist)+.13*quarry,.20,.84))
        coarse=np.maximum(coarse,band*np.clip(.40+.18*patch+.13*slow+.25*quarry+.14*smooth(1.3,3.0,dist),.10,.88))
        def at(s):return np.array([np.interp(s,chain,line[:,axis]) for axis in (0,1)])
        station=rng.uniform(3.,8.)
        while station<chain[-1]-2.:
            s=station
            station+=rng.uniform(5.3,11.9)+(rng.uniform(4.,12.) if rng.random()<.20 else 0.)
            along=at(s+1.25)-at(s-1.25);along/=np.linalg.norm(along)
            center=at(s)+np.array([-along[1],along[0]])*rng.uniform(-1.03,1.03)
            angle=np.arctan2(along[1],along[0])+rng.uniform(-.15,.15)
            length=rng.uniform(.72,1.65);width=rng.uniform(.28,.66)
            radius=math.hypot(length,width)+2.*STEP
            px,py=(center-np.array(ORIGIN))/STEP
            if not (0<=int(px)<WIDTH and 0<=int(py)<HEIGHT) or exterior[int(py),int(px)]<.95:continue
            if any(np.linalg.norm(center-p['xy'])<radius+p['guard_m'] for p in stamps):continue
            i=len(stamps)+1
            if i>255:raise ValueError('Track ID field needs a wider format')
            uv=(center-np.array(ORIGIN))/np.array([WIDTH*STEP,HEIGHT*STEP])
            cx16,cy16=np.rint(uv*65535).astype(int);phase=[rng.random(),(rng.choice([.075,.55])+rng.uniform(-.048,.048))%1.]
            encode=lambda a:np.rint(np.clip(a,0,1)*255).astype('u1')
            lut[0,i]=[cx16>>8,cx16&255,cy16>>8,cy16&255]
            lut[1,i]=encode(np.array([np.cos(angle)*.5+.5,np.sin(angle)*.5+.5,*phase]))
            lut[2,i]=encode(np.array([length/2.,width,rng.random(),rng.uniform(.52,.86)]))
            sx=slice(max(0,int(px-radius/STEP)-1),min(WIDTH,int(px+radius/STEP)+2))
            sy=slice(max(0,int(py-radius/STEP)-1),min(HEIGHT,int(py+radius/STEP)+2))
            ids[sy,sx][np.hypot(x[sy,sx]-center[0],y[sy,sx]-center[1])<radius]=i
            stamps.append(dict(id=i,road=name,station_m=round(s,2),xy=center.tolist(),guard_m=radius))
    field=np.stack((exterior*lane,stone,coarse),axis=-1)
    Image.fromarray(np.dstack((np.rint(field*255).clip(0,255).astype('u1'),ids))).save(src/'T_RoadMixField.png')
    Image.fromarray(lut).save(src/'T_TrackFrames.png')
    return stamps

if __name__=='__main__':
    output,terrain,existing=map(Path,sys.argv[1:])
    scans=palettes(output,existing)
    stamps=placement(output,terrain)
    (output/'road-mix.json').write_text(json.dumps(dict(seed=SEED,scans=scans,frames=stamps,field_origin_m=ORIGIN,step_m=STEP),indent=2))
