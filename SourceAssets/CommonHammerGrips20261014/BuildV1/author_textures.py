"""Author seamless textile/leather PBR tiles from periodic physical-height fields."""
import bpy,numpy as np
from pathlib import Path
P=Path(__file__).resolve().parent;OUT=P/'Textures';OUT.mkdir(exist_ok=True)
N=2048;TILE=.12;rng=np.random.default_rng(20261014)
y,x=np.mgrid[0:N,0:N].astype(np.float32)/N
def noise(period):
    grid=rng.random((period,period)).astype(np.float32)
    xx=x*period;yy=y*period;ix=xx.astype(int);iy=yy.astype(int)
    tx=xx-ix;ty=yy-iy;tx=tx*tx*(3-2*tx);ty=ty*ty*(3-2*ty)
    return ((1-tx)*grid[iy%period,ix%period]+tx*grid[iy%period,(ix+1)%period])*(1-ty)+((1-tx)*grid[(iy+1)%period,ix%period]+tx*grid[(iy+1)%period,(ix+1)%period])*ty
macro=noise(9);fine=noise(340);grain=noise(140)
def save(name,values,color=False):
    if values.ndim==2:values=np.repeat(values[:,:,None],3,axis=2)
    rgba=np.ones((N,N,4),dtype=np.float32);rgba[:,:,:3]=np.clip(values,0,1)
    image=bpy.data.images.new(name,width=N,height=N,alpha=True)
    image.colorspace_settings.name='Non-Color';image.pixels.foreach_set(rgba.ravel())
    image.filepath_raw=str(OUT/(name+'.png'));image.file_format='PNG';image.save()
    if color:image.colorspace_settings.name='sRGB'
    return image
def maps(kind,height,base,rough):
    # OpenGL tangent normal; UE importer flips green for DirectX sampling.
    dx=(np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))/(2*TILE/N)
    dy=(np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))/(2*TILE/N)
    norm=np.stack((-dx,-dy,np.ones_like(dx)),axis=2);norm/=np.linalg.norm(norm,axis=2)[:,:,None]
    save('T_HammerGrip_'+kind+'_BaseColor',base,True)
    save('T_HammerGrip_'+kind+'_Normal',norm*.5+.5)
    orm=np.stack((.88+.12*grain,rough,np.zeros_like(x)),axis=2)
    save('T_HammerGrip_'+kind+'_ORM',orm)
weave_x=(.5+.5*np.cos(x*128*2*np.pi))**.6
weave_y=(.5+.5*np.cos(y*128*2*np.pi))**.6
over=((np.floor(x*128)+np.floor(y*128)).astype(int)%2)==0
weave=np.where(over,weave_x*(.6+.4*weave_y),weave_y*(.6+.4*weave_x))
height=(weave*.85+fine*.15)*.00010
shade=.76+.22*weave+.12*(macro-.5)+.06*(fine-.5)
maps('Woven',height,shade[:,:,None]*np.array([.47,.43,.355]),np.clip(.87+.09*(1-weave),0,1))
cells=noise(115);pores=(np.maximum(0,.28-grain)/.28)**2
height=(cells*.65+grain*.25+fine*.1-pores*.3)*.000075
shade=.73+.22*cells+.12*macro+.06*(fine-.5)
maps('Leather',height,shade[:,:,None]*np.array([.30,.154,.075]),np.clip(.54+.12*(1-cells)+.06*macro,0,1))
print('GRIP_PBR_TILES_SAVED',flush=True)
