"""Convert commissioned dragon/cloud height art into geometry and 4K PBR data."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
P=Path(__file__).resolve().parent
WIDTH=.144; HEIGHT=.164

def artwork(size):
    im=Image.open(P/'Ornament/DragonCloud_HeightSource.png').convert('RGBA')
    # Remove transparent margins; never use the image's border as a mount pivot.
    alpha=im.getchannel('A').point(lambda a:255 if a>180 else 0)
    im=im.crop(alpha.getbbox()).resize(size,Image.Resampling.LANCZOS)
    rgba=np.asarray(im,dtype=np.float32)/255
    mask=Image.fromarray((rgba[:,:,3]>.60).astype('uint8')*255)
    mask=mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
    mask=np.asarray(mask)>128
    rows,cols=size[1],size[0]
    xx,yy=np.meshgrid(np.linspace(-WIDTH/2,WIDTH/2,cols),np.linspace(HEIGHT/2,-HEIGHT/2,rows))
    # The sculpted cloud perforations remain open. The hidden load-bearing center
    # is filled, then covered by the fitted front/rear ferrules.
    core=(abs(xx-.0015)<.0168)&(abs(yy)<.018)
    mask|=core
    lum=(rgba[:,:,:3]*np.array([.2126,.7152,.0722])).sum(axis=2)
    lum[core]=.40
    return lum,mask

def relief(lum):
    # The low opaque ground is solid metal; ivory ribs are actual raised metal.
    a=np.clip((lum-.25)/.69,0,1)
    return .0025*a**1.45

def geometry_data(size=(385,449)):
    lum,mask=artwork(size)
    lum=np.asarray(Image.fromarray((lum*255).astype('uint8')).filter(ImageFilter.GaussianBlur(1.0)),dtype=np.float32)/255
    return relief(lum),mask

def srgb(linear):
    return np.where(linear<=.0031308,linear*12.92,1.055*np.maximum(linear,0)**(1/2.4)-.055)

def bake():
    n=4096; rng=np.random.default_rng(20261002)
    color=np.zeros((n,n,3),np.uint8); orm=np.zeros_like(color)
    normal=np.zeros_like(color);normal[:]=[128,128,255]
    x0,x1=int(.02*n),int(.78*n);y0,y1=int(.02*n),int(.98*n)
    lum,mask=artwork((x1-x0,y1-y0));h=relief(lum)
    height_img=Image.fromarray((h/.0025*65535).astype('uint16'))
    height_img.save(P/'Textures/TangDao_XuanCloudGuard_Height16.png')
    # Stable material zones remove photographic highlights from the source art.
    gilded=np.clip((lum-.31)/.25,0,1);gilded=gilded*gilded*(3-2*gilded)
    age=np.asarray(Image.fromarray((rng.random(lum.shape)*255).astype('uint8')).filter(ImageFilter.GaussianBlur(6)),dtype=np.float32)/255
    grain=rng.normal(0,.007,lum.shape).astype('float32')
    raised=np.array([.54,.325,.105],np.float32)
    recessed=np.array([.032,.025,.017],np.float32)
    linear=recessed[None,None,:]*(1-gilded[:,:,None])+raised[None,None,:]*gilded[:,:,None]
    linear*=np.clip(.93+(age-.5)*.25+grain,.78,1.12)[:,:,None]
    color[:]=np.clip(srgb(raised*.92)*255,0,255).astype('uint8')
    color[y0:y1,x0:x1]=np.clip(srgb(linear)*255,0,255).astype('uint8')
    ao=np.clip(.64+.34*gilded,0,1)
    rough=np.clip(.46-.19*gilded+(age-.5)*.07+grain,.23,.51)
    metal=np.clip(.92+.07*gilded,0,1)
    orm[:]=[247,82,251]
    orm[y0:y1,x0:x1]=np.stack([ao,rough,metal],2)*255
    # Fine incised scales and chiselled edges supplement, rather than duplicate,
    # the broad geometric relief. Low-frequency height belongs to the mesh.
    blurred=np.asarray(Image.fromarray((h/.0025*255).astype('uint8')).filter(ImageFilter.GaussianBlur(4)),dtype=np.float32)/255*.0025
    micro=.25*np.clip(h-blurred,-.00010,.00010)+grain*.000025
    dy,dx=np.gradient(micro,HEIGHT/(y1-y0),WIDTH/(x1-x0))
    nn=np.stack([-dx,dy,np.ones_like(dx)],2);nn/=np.linalg.norm(nn,axis=2)[:,:,None]
    normal[y0:y1,x0:x1]=np.clip((nn*.5+.5)*255,0,255).astype('uint8')
    # Reserved ferrule UV strip: engraved continuous cloud waves and fine hatch.
    xa,xb=int(.81*n),int(.99*n)
    vv,uu=np.meshgrid(np.linspace(1,0,n),np.linspace(0,1,xb-xa),indexing='ij')
    wave=np.sin(uu*8*np.pi+1.8*np.sin(vv*10*np.pi))
    ridge=np.exp(-((np.abs(wave)-.78)/.10)**2)
    bands=np.exp(-((np.sin(vv*14*np.pi))/.17)**2)
    pat=np.clip(.45+.50*ridge+.35*bands,0,1)
    lc=np.array([.16,.087,.028])[None,None,:]*(1-pat[:,:,None])+raised[None,None,:]*pat[:,:,None]
    color[:,xa:xb]=np.clip(srgb(lc)*255,0,255).astype('uint8')
    orm[:,xa:xb,0]=np.clip(.74+.25*pat,0,1)*255
    orm[:,xa:xb,1]=np.clip(.40-.13*pat,0,1)*255
    ch=.00010*(ridge+bands*.5)
    dz,da=np.gradient(ch,.064/n,.13/(xb-xa))
    nn=np.stack([-da,-dz,np.ones_like(da)],2);nn/=np.linalg.norm(nn,axis=2)[:,:,None]
    normal[:,xa:xb]=np.clip((nn*.5+.5)*255,0,255).astype('uint8')
    for key,a in [('BaseColor',color),('ORM',orm),('Normal',normal)]:
        Image.fromarray(a,'RGB').save(P/'Textures'/('TangDao_XuanCloudGuard_'+key+'.png'))
    # Author mesh uses this moderate grid without depending on Blender's PIL.
    gh,gm=geometry_data()
    np.savez_compressed(P/'Ornament/guard_geometry.npz',height=gh,mask=gm)
    print('XUAN_CLOUD_GUARD_PBR_BAKED',flush=True)

if __name__=='__main__':bake()
