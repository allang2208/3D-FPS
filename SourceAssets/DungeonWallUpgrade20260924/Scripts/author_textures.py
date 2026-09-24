"""Prepare scan PBR, physical grit and a cleaned Fab derivative. No game renders."""
import hashlib,json,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageFilter
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored/Textures';OUT.mkdir(parents=True,exist_ok=True)
PH=ROOT/'Sources/PolyHaven';rng=np.random.default_rng(924683)
manifest={'stage':'authored','textures':{},'normal_convention':'DirectX, do not flip green','production_replacement':False}
def read(p,n=None):
    with Image.open(p) as im:
        if n:im=im.resize((n,n),Image.Resampling.LANCZOS)
        a=np.array(im)
        return a.astype(np.float32)/(65535 if a.dtype==np.uint16 or a.max()>255 else 255)
def blur(a,r):
    return np.array(Image.fromarray(np.uint8(np.clip(a,0,1)*255)).filter(ImageFilter.GaussianBlur(r)),dtype=np.float32)/255
def save(name,a,height=False):
    p=OUT/(name+'.png');Image.fromarray((np.clip(a,0,1)*(65535 if height else 255)).astype(np.uint16 if height else np.uint8)).save(p)
    manifest['textures'][name]={'file':str(p),'size':list(a.shape[:2]),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    print('AUTHORED',name,a.shape,flush=True)
def normal_from_cm(h,tile_cm):
    # Image v points down. The shader consumes a DirectX tangent normal (+green = +v).
    d=tile_cm/h.shape[0];dx=(np.roll(h,-1,1)-np.roll(h,1,1))/(2*d);dy=(np.roll(h,-1,0)-np.roll(h,1,0))/(2*d)
    n=np.stack((-dx,-dy,np.ones_like(h)),-1);n/=np.linalg.norm(n,axis=2,keepdims=True)
    return n*.5+.5

# Complete scan channels stay registered. Alter the colour grade, not their positions.
for kind,n,target in [('Wall',4096,[.53,.545,.53]),('Mortar',2048,[.48,.47,.435])]:
    col=read(PH/'plastered_wall_diff_4k.jpg',n)
    lum=col@np.array([.2126,.7152,.0722],np.float32)
    grain_color=np.clip((lum-lum.mean())*1.35,-.16,.16)
    col=np.clip(np.array(target,dtype=np.float32)+grain_color[...,None]+(col-lum[...,None])*.22,0,1)
    normal=read(PH/'plastered_wall_nor_dx_4k.png',n)[...,:3]
    surf=read(PH/'plastered_wall_arm_4k.png',n)[...,:3]
    # The surface texture uses conventional ORM: R=AO G=roughness B=metallic.
    surf[...,0]=.65+.35*surf[...,0]
    surf[...,1]=np.clip((.66 if kind=='Wall' else .76)+surf[...,1]*.18,.60,.94);surf[...,2]=0
    h=read(PH/'plastered_wall_disp_4k.png',n)
    if h.ndim==3:h=h[...,0]
    low,high=np.percentile(h,[.2,99.8]);h=np.clip((h-low)/max(high-low,.0001),0,1)
    for channel,a in [('BaseColor',col),('Normal',normal),('ORM',surf),('Height',h)]:save(kind+'_'+channel,a,channel=='Height')
    del col,lum,normal,surf,h,grain_color

# Angular, variably embedded grains with sparse irregular pits. 32cm physical tile.
N=1024;tile=32.;h=np.zeros((N,N),np.float32);tint=np.zeros_like(h);rough=np.full_like(h,.78)
for i in range(8800):
    cx,cy=rng.uniform(0,N,2);r=float(np.clip(rng.lognormal(1.05,.43),1.2,7.0))
    pit=(i%7==0);rx,ry=r*rng.uniform(.7,1.2),r*rng.uniform(.65,1.25)
    reach=int(max(rx,ry)*1.4+2);xs=np.arange(int(cx)-reach,int(cx)+reach+1);ys=np.arange(int(cy)-reach,int(cy)+reach+1)
    yy,xx=np.meshgrid((ys-cy)/ry,(xs-cx)/rx,indexing='ij');ang=rng.uniform(0,math.tau)
    xp=xx*np.cos(ang)-yy*np.sin(ang);yp=xx*np.sin(ang)+yy*np.cos(ang)
    angle=np.arctan2(yp,xp);facets=int(rng.integers(4,8))
    radius=np.sqrt(xp*xp+yp*yp)*(1+.14*np.cos(angle*facets+rng.uniform(0,6.28)))
    edge=np.clip((1-radius)*r/1.1,0,1)
    relief=rng.uniform(.008,.035)*(1+.22*xp-.15*yp)*edge
    if pit:relief=-relief*1.6
    region=np.ix_(ys%N,xs%N);old=h[region]
    h[region]=np.minimum(old,relief) if pit else np.maximum(old,relief)
    tint[region]=tint[region]*(1-edge)+rng.uniform(-.065,.065)*edge
    rough[region]=rough[region]*(1-edge)+rng.uniform(.64,.91)*edge
save('Grain_Normal',normal_from_cm(h,tile))
save('Grain_Surface',np.stack((rough,.5+tint,np.clip(1+np.minimum(h,0)*3,.80,1)),-1))
manifest['grain']={'tile_cm':tile,'height_range_cm':float(np.ptp(h)),'construction':'seeded angular inclusions and irregular pits; periodic wrapping; physically derived DX normals','seed':924683}

# Reuse the acquired Fab scan, with clean-patch rejection and broad overlapping blends.
# This is new source-pixel synthesis, not an enlargement of the old 1K quilt.
provenance=json.loads((ROOT.parent/'DungeonWallDamage20260923/Sources/provenance.json').read_text())
source=[]
for udim in ['1003','1001']:
    parts=[]
    for chan in ['BaseColor','Normal','ORM']:
        e=next(e for e in provenance['source_textures'] if '_'+chan+'_' in e['file'] and ('.'+udim+'.png') in e['file'])
        with Image.open(e['file']) as im:
            box=tuple(int(v*im.size[j%2]) for j,v in enumerate(e['crop']));im=im.crop(box).convert('RGB');a=np.asarray(im,dtype=np.float32)/255
        parts.append(a)
    a=np.concatenate(parts,axis=2)
    # Remove broad capture lighting/blue cast while retaining material-scale variation.
    col=a[...,:3];original=col.copy();b=blur(col,24);mean=np.array([.475,.47,.45],np.float32)
    a[...,:3]=np.clip(mean+(col-b)*.92+(b-b.mean((0,1)))*.18,0,1)
    source.append((a,original))
N=2048;patch=256;step=128;canvas=np.zeros((N,N,9),np.float32);weight=np.zeros((N,N,1),np.float32)
window=(np.sin(np.pi*(np.arange(patch)+.5)/patch)**2).astype(np.float32);window=(window[:,None]*window[None,:])[...,None]
for y in range(0,N,step):
    for x in range(0,N,step):
        choices=[]
        for _ in range(24):
            a,raw=source[int(rng.integers(len(source)))];sy=int(rng.integers(0,a.shape[0]-patch));sx=int(rng.integers(0,a.shape[1]-patch))
            c=a[sy:sy+patch,sx:sx+patch];r=raw[sy:sy+patch,sx:sx+patch]
            red=np.maximum(r[...,0]-r[...,1]-.018,0).mean()
            lum=r.mean(2);edge=np.mean(np.abs(np.diff(lum,axis=0))>.07)+np.mean(np.abs(np.diff(lum,axis=1))>.07)
            score=red*40+edge*3+np.mean(lum<.16)*2
            choices.append((score,c))
        c=min(choices,key=lambda q:q[0])[1]
        idx=np.ix_((np.arange(patch)+y)%N,(np.arange(patch)+x)%N)
        canvas[idx]+=c*window;weight[idx]+=window
canvas/=np.maximum(weight,1e-5)
n=canvas[...,3:6]*2-1;n/=np.maximum(np.linalg.norm(n,axis=2,keepdims=True),1e-5)
save('FabSection_BaseColor',canvas[...,:3]);save('FabSection_Normal',n*.5+.5)
orm=canvas[...,6:9];orm[...,0]=np.clip(orm[...,0],.6,1);orm[...,1]=np.clip(orm[...,1],.7,.96);orm[...,2]=0
save('FabSection_ORM',orm)
# No fabricated height from scan colour: this scan has no height map.
manifest['fab']={'source_title':provenance['title'],'url':provenance['url'],'source_receipt':str(ROOT.parent/'DungeonWallDamage20260923/Sources/provenance.json'),
    'method':'2048px periodic weighted overlap synthesis from original scan pixels; reject paint/seam candidates, reduce capture cast, coherent PBR blending and normal renormalization',
    'height_map':False,'redistribution':'Local game use; not a standalone redistributable material pack'}
(ROOT/'Authored/materials.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('WALL_UPGRADE_TEXTURES_AUTHORED',len(manifest['textures']),flush=True)
