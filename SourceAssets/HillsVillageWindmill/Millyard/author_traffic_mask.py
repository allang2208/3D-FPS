"""Traffic under the mill door, barrow wheel and straw stack, in site-local cm."""
from pathlib import Path
import numpy as np
from PIL import Image

root=Path(__file__).resolve().parent/'WorkDetails'
root.mkdir(exist_ok=True)
w,h=1536,1024
rng=np.random.default_rng(1936)
x=np.linspace(-850,760,w)[None,:]
y=np.linspace(210,1330,h)[:,None]

def noise(width,height):
    tiles=Image.fromarray(rng.integers(0,256,(height,width),dtype=np.uint8))
    return np.asarray(tiles.resize((w,h),Image.Resampling.BICUBIC),dtype=np.float32)/255-.5

coarse=noise(30,22)
medium=noise(100,65)
fine=noise(480,300)
footprint=np.zeros((h,w),np.float32)

def tread(points, strength):
    global footprint
    band=np.zeros_like(footprint)
    for (ax,ay,aw),(bx,by,bw) in zip(points,points[1:]):
        dx,dy=bx-ax,by-ay
        t=np.clip(((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy),0,1)
        d=np.hypot(x-ax-t*dx,y-ay-t*dy)
        width=aw+t*(bw-aw)
        a=np.clip(1-d/width+coarse*.45+medium*.19,0,1)
        band=np.maximum(band,a*a*(3-2*a))
    footprint=np.maximum(footprint,band*strength)

tread([(0,405,132),(-17,545,165),(-22,712,132),(-86,931,118),(-160,1170,72),(-201,1275,15)],.66)
tread([(-36,537,97),(-176,542,96),(-348,495,91),(-492,513,71),(-661,474,56)],.78)
tread([(173,411,90),(311,398,106),(414,448,92),(416,547,79),(330,673,83),(166,792,76),(-48,954,51)],.76)
tread([(364,384,9),(427,433,13),(453,500,16),(448,556,12),(412,620,11),(345,689,10),(267,755,12),(170,814,9),(75,877,7)],.96)
opacity=np.clip(footprint*(.91+coarse*.62+medium*.44+fine*.46)+np.maximum(0,footprint-.04)*rng.normal(0,.065,(h,w)),0,1)
Image.fromarray((opacity*255+.5).astype('uint8')).save(root/'MillApronTraffic.png')
