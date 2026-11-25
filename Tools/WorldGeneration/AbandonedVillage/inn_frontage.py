"""Wear at the service court and the link from the south village lane to the main street."""
import numpy as np
from PIL import Image
from village_tread import ramp,soil_variation

def patch(packed,height,gravel,plan,shape):
    from village_ground_relief import frame,box,distance
    yaw=shape['angle']-90
    center=shape['shell_center']
    ex,ey=plan['surface_extent_m']
    def clear(x,y):
        u,v=frame(x,y,center,yaw)
        return np.minimum.reduce(np.broadcast_arrays(box(u,v,(-.40,2.01),(7.22,6.45)),
            box(u,v,(-3.5,-9.42),(3.7,2.04)),box(u,v,(.76,-7.8),(1.40,3.7))))
    xx=np.linspace(-ex,ex,height.shape[1])[None,:];yy=np.linspace(-ey,ey,height.shape[0])[:,None]
    height*=ramp(clear(xx,yy)/.88)
    stones=[p for p in gravel if clear(p[0]*.01,p[1]*.01)>.01*p[2]+.14]
    a=np.array(packed);h,w=a.shape[:2]
    xs=np.flatnonzero(abs(((np.arange(w)+.5)/w-.5)*2*ex-center[0])<13.)
    ys=np.flatnonzero((((np.arange(h)+.5)/h-.5)*2*ey>0)&(((np.arange(h)+.5)/h-.5)*2*ey<center[1]+9.))
    x=((xs[None,:]+.5)/w-.5)*2*ex;y=((ys[:,None]+.5)/h-.5)*2*ey
    u,v=frame(x,y,center,yaw)
    grain=soil_variation(x,y,.42,24901);coarse=soil_variation(x,y,1.6,24903)
    apron=np.exp(-((u-.4-.44*np.sin((v+4.)*.36))/1.24)**2)*ramp((-3.98-v)/.45)*ramp((v+13.)/2)
    tether=np.maximum.reduce([np.exp(-((u-c+.12*coarse)/.85)**2-((v+9.56)/1.62)**4) for c in (-5.57,-3.50,-1.43)])
    crosswalk=np.exp(-((v+10.82+.04*u)/.85)**2)*ramp((u+7.)/1.4)*ramp((1.55-u)/1.)
    link=distance(x,y,[(-9.4,2.2),(-8.35,5.8),(-8.10,10.0),(-9.9,14.),(-14.1,17.6),
                         (center[0]-.60,center[1]-10.5),(center[0]-.10,center[1]-6.2)])
    wear=np.maximum.reduce([apron,.91*tether,.77*crosswalk,.9*np.exp(-(link/(1.07+.12*coarse))**2)])*np.clip(.84+.09*coarse+.08*grain,.60,1)
    tile=a[ys[0]:ys[-1]+1,xs[0]:xs[-1]+1]
    for idx,strength in [(1,.97),(2,.46)]:
        tile[:,:,idx]=np.maximum(tile[:,:,idx],np.rint(wear*strength*255).astype('uint8'))
    if shape and plan['tavern']['inn'].get('hall_road'):
        from inn_road import patch as fit_road
        return fit_road(Image.fromarray(a),height,stones,plan,shape)
    return Image.fromarray(a),height,stones
