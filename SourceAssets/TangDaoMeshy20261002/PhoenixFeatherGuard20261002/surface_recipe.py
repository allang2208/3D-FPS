"""Physical phoenix feather relief, pierced outline and authored gilt/garnet PBR."""
from pathlib import Path
from collections import deque
import json,numpy as np
from PIL import Image,ImageFilter
P=Path(__file__).resolve().parent
WIDTH=.134;HEIGHT=.178;ART_OFFSET_X=.020;RELIEF=.0031
im=Image.open(P/'Ornament/PhoenixCloud_HeightSource.png').convert('RGBA')
bbox=im.getchannel('A').point(lambda a:255 if a>180 else 0).getbbox()
SOURCE=im.crop(bbox)

def artwork(size):
    rgba=np.asarray(SOURCE.resize(size,Image.Resampling.LANCZOS),dtype=np.float32)/255
    mask=Image.fromarray((rgba[...,3]>.60).astype('uint8')*255).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
    mask=np.asarray(mask)>128
    cols,rows=size;xx,yy=np.meshgrid(np.linspace(-WIDTH/2+ART_OFFSET_X,WIDTH/2+ART_OFFSET_X,cols),np.linspace(HEIGHT/2,-HEIGHT/2,rows))
    core=(abs(xx-.0015)<.017)&(abs(yy)<.018)
    mask|=core
    lum=rgba[...,:3]@np.array([.2126,.7152,.0722],np.float32)
    red=(rgba[...,0]>rgba[...,1]*1.7)&(rgba[...,0]>rgba[...,2]*1.6)&(rgba[...,0]>.16)
    # Source's two red oval locators become separate real garnet cabochons.
    # The metal under each stone is solid, not a red printed decal.
    lum=np.where(red,.53,lum);lum=np.where(core,.40,lum)
    return lum,mask

def relief(lum):
    return RELIEF*np.clip((lum-.24)/.70,0,1)**1.4

def gemstones():
    a=np.asarray(SOURCE,dtype=np.float32)/255
    selected=(a[...,0]>a[...,1]*1.7)&(a[...,0]>a[...,2]*1.6)&(a[...,0]>.16)&(a[...,3]>.60)
    seen=np.zeros(selected.shape,bool);components=[]
    for y,x in zip(*np.where(selected)):
        if seen[y,x]:continue
        seen[y,x]=True;q=deque([(int(y),int(x))]);points=[]
        while q:
            yy,xx=q.popleft();points.append((yy,xx))
            for dy,dx in [(-1,0),(1,0),(0,-1),(0,1)]:
                ny,nx=yy+dy,xx+dx
                if 0<=ny<selected.shape[0] and 0<=nx<selected.shape[1] and selected[ny,nx] and not seen[ny,nx]:seen[ny,nx]=True;q.append((ny,nx))
        if len(points)>30:components.append(points)
    result=[];height,width=selected.shape
    for points in sorted(components,key=len,reverse=True)[:2]:
        p=np.asarray(points);cy,cx=p.mean(axis=0)
        rx=(p[:,1].max()-p[:,1].min()+1)/(width-1)*WIDTH/2
        ry=(p[:,0].max()-p[:,0].min()+1)/(height-1)*HEIGHT/2
        result.append({'x_m':-WIDTH/2+ART_OFFSET_X+WIDTH*cx/(width-1),'y_m':HEIGHT/2-HEIGHT*cy/(height-1),
                       'radius_x_m':rx,'radius_y_m':ry,'dome_height_m':.0021 if len(points)>1200 else .0015})
    return result

def srgb(linear):return np.where(linear<=.0031308,linear*12.92,1.055*np.maximum(linear,0)**(1/2.4)-.055)

def save(family,key,a):
    Image.fromarray(np.clip(a*255+.5,0,255).astype('uint8')).save(P/'Textures'/f'TangDao_PhoenixFeatherGuard_{family}_{key}.png')

def bake():
    n=4096;rng=np.random.default_rng(261002)
    color=np.zeros((n,n,3),np.float32);orm=np.zeros_like(color);normal=np.zeros_like(color);normal[:]=[.5,.5,1]
    x0,x1=int(.02*n),int(.78*n);y0,y1=int(.02*n),int(.98*n)
    lum,mask=artwork((x1-x0,y1-y0));h=relief(lum)
    Image.fromarray((h/RELIEF*65535).astype('uint16')).save(P/'Textures/TangDao_PhoenixFeatherGuard_Height16.png')
    raised=np.clip((lum-.27)/.32,0,1);raised=raised*raised*(3-2*raised)
    grain=rng.normal(0,.006,lum.shape).astype('float32')
    age=np.asarray(Image.fromarray((rng.random((128,96))*255).astype('uint8')).resize((lum.shape[1],lum.shape[0]),Image.Resampling.BICUBIC),dtype=np.float32)/255
    gold=np.array([.77,.515,.185],np.float32);bronze=np.array([.105,.061,.025],np.float32)
    linear=bronze*(1-raised[...,None])+gold*raised[...,None]
    linear*=np.clip(.96+.12*(age-.5)+grain,.86,1.07)[...,None]
    color[:]=srgb(gold*.97);color[y0:y1,x0:x1]=srgb(linear)
    orm[:]=[.99,.27,.98]
    orm[y0:y1,x0:x1]=np.stack([.77+.22*raised,.46-.205*raised+.025*(age-.5)+grain,.88+.11*raised],2)
    blurred=np.asarray(Image.fromarray((h/RELIEF*255).astype('uint8')).filter(ImageFilter.GaussianBlur(5)),dtype=np.float32)/255*RELIEF
    micro=.22*np.clip(h-blurred,-.00013,.00013)+grain*.000023
    dy,dx=np.gradient(micro,HEIGHT/(y1-y0),WIDTH/(x1-x0))
    nn=np.stack([-dx,dy,np.ones_like(dx)],2);nn/=np.linalg.norm(nn,axis=2)[...,None]
    normal[y0:y1,x0:x1]=nn*.5+.5
    # Collar strip is based on actual scroll artwork, unwrapped around the
    # interface perimeter; no globally projected decorative sine waves.
    xa,xb=int(.81*n),int(.99*n);cloud=SOURCE.crop((int(SOURCE.width*.025),int(SOURCE.height*.24),int(SOURCE.width*.34),int(SOURCE.height*.76)))
    tile=np.asarray(cloud.resize((xb-xa,650),Image.Resampling.LANCZOS),dtype=np.float32)/255
    tile_lum=tile[...,:3]@np.array([.2126,.7152,.0722],np.float32)
    tiled=tile_lum[np.arange(n)%650]
    pat=np.clip((tiled-.28)/.32,0,1);pat=pat*pat*(3-2*pat)
    lc=np.array([.20,.105,.033],np.float32)*(1-pat[...,None])+gold*pat[...,None]
    color[:,xa:xb]=srgb(lc);orm[:,xa:xb]=np.stack([.83+.16*pat,.40-.14*pat,np.ones_like(pat)*.98],2)
    dz,da=np.gradient(.000026*pat,.064/n,.13/(xb-xa))
    nn=np.stack([-da,-dz,np.ones_like(da)],2);nn/=np.linalg.norm(nn,axis=2)[...,None]
    normal[:,xa:xb]=nn*.5+.5
    for key,a in [('BaseColor',color),('ORM',orm),('Normal',normal)]:save('Gilt',key,a)
    lum,gm=artwork((385,513))
    lum=np.asarray(Image.fromarray((lum*255).astype('uint8')).filter(ImageFilter.GaussianBlur(.85)),dtype=np.float32)/255
    np.savez_compressed(P/'Ornament/guard_geometry.npz',height=relief(lum),mask=gm)
    (P/'Ornament/gemstones.json').write_text(json.dumps(gemstones(),indent=2)+'\n',encoding='utf-8')
    # Garnet stays dielectric. Faceted/curved geometry supplies real highlights.
    n=512;u,v=np.meshgrid(np.linspace(-1,1,n),np.linspace(-1,1,n));depth=np.clip(u*u+v*v,0,1)
    red=np.array([.255,.0028,.0065])*(1-.26*depth[...,None])
    save('Garnet','BaseColor',srgb(red));save('Garnet','ORM',np.stack([depth*0+1,depth*.035+.16,depth*0],2))
    save('Garnet','Normal',np.stack([depth*0+.5,depth*0+.5,depth*0+1],2))
    print('PHOENIX_FEATHER_GUARD_PBR_BAKED',flush=True)

if __name__=='__main__':bake()
