"""Inn apron and village street junction. Dimensions in metres, relief in centimetres."""
import math
import numpy as np
from PIL import Image
from village_tread import ramp,tread
from village_ground_relief import frame,box

def grain(x,y):
    return .40*np.sin(2.93*x+.84*y)+.29*np.sin(1.42*y-1.91*x)+.17*np.cos(5.2*x+3.1*y)+.14*np.sin(8.8*y-.78*x)

def patch(packed,height,gravel,plan,shape):
    spec=plan['tavern']['inn']['hall_road'];stations=spec['stations']
    ex,ey=plan['surface_extent_m'];center=shape['shell_center'];angle=shape['angle']-90
    def surfaces(x,y):
        n=grain(x,y); gap=tread(x,y,stations)
        edge=ramp((gap+.8+.24*n)/1.15)
        u,v=frame(x,y,center,angle)
        contact=ramp(box(u,v,(-3.5,-8.45),(3.47,1.63))/.80)*ramp((-4.4-v)/1.0)
        runs=np.maximum.reduce([np.exp(-(tread(x,y,[(a,b,0) for a,b,_ in stations],side*(.74+.1*np.sin(y*.63)))/.34)**2) for side in (-1,1)])
        runs*=.58+.42*ramp(.5+.5*np.sin(.72*y+.4*x))
        wall=np.zeros_like(gap)
        for retired in spec['retired_walls']:
            a,b,w=retired['line']
            wall=np.maximum(wall,ramp((tread(x,y,[(*a,w),(*b,w)])+.72)/.90))
        return n,gap,edge,contact,runs,wall
    img=np.array(packed);h,w=img.shape[:2]
    xs=np.flatnonzero((abs(((np.arange(w)+.5)/w-.5)*2*ex+16.5)<13.5))
    ys=np.flatnonzero((abs(((np.arange(h)+.5)/h-.5)*2*ey-13.5)<14.3))
    x=((xs[None,:]+.5)/w-.5)*2*ex;y=((ys[:,None]+.5)/h-.5)*2*ey
    n,g,e,c,r,wall=surfaces(x,y)
    tile=img[ys[0]:ys[-1]+1,xs[0]:xs[-1]+1];cover=np.maximum(e,.78*wall)
    mineral=np.clip(.28+.11*n+.23*np.exp(-((g-.08)/.66)**2)+.13*r,0,1)
    # Packed channels G/B are exposed soil/mineral; R and alpha carry independent terrain data.
    for i,target in ((1,255*np.clip(.78+.09*n+.13*r+.07*ramp(g/2),0,1)),(2,255*mineral)):
        tile[:,:,i]=np.rint(tile[:,:,i]*(1-cover)+target*cover).astype('uint8')
    x=np.linspace(-ex,ex,height.shape[1])[None,:];y=np.linspace(-ey,ey,height.shape[0])[:,None]
    n,g,e,c,r,wall=surfaces(x,y);cover=np.maximum(e,wall)
    htarget=(1.5+.9*n-5.2*r+1.15*np.exp(-((g-.02)/.70)**2))*c
    height=height*(1-cover)+cover*htarget
    def field(x,y):return float(tread(np.array([[x]]),np.array([[y]]),stations).item())
    from layout_geometry import wall_segments
    walls=list(wall_segments(plan))
    rng=np.random.default_rng(310725)
    # A repeatable pocket is redistributed only inside this road's bare tread and shoulders.
    kept=[p for p in gravel if field(p[0]/100,p[1]/100)<-1.05]
    for idx,(a,b) in enumerate(zip(stations,stations[1:])):
        dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
        if idx>=len(stations)-3:continue
        for side in (-1,1):
            for t in sorted(rng.uniform(.07,.96,2)):
                for _ in range(rng.integers(2,6)):
                    tt=np.clip(t+rng.normal(0,.055),.02,.98);spread=(a[2]+(b[2]-a[2])*tt+rng.uniform(-.27,.57))*side
                    xx=a[0]+tt*dx+spread*dy/length;yy=a[1]+tt*dy-spread*dx/length
                    if yy<3.8:continue
                    if any(_near(xx,yy,line[1:3],line[3:5])<width+.33 for line,width in walls):continue
                    cx,cy=round(xx*100),round(yy*100);s=int(rng.integers(5,13))
                    if any((cx-ox)**2+(cy-oy)**2<(.71*(s+sz)+2)**2 for ox,oy,sz,_,_ in kept):continue
                    kept.append((cx,cy,s,int(rng.integers(256)),int(rng.integers(3))))
    return Image.fromarray(img),height,sorted(kept,key=lambda p:(p[1],p[0]))

def _near(x,y,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]
    t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/max(.00001,dx*dx+dy*dy)))
    return math.hypot(x-a[0]-t*dx,y-a[1]-t*dy)
