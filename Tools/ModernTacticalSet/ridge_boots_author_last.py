"""Pattern cutting and sole development based on the Zephyr MK2 HI Coyote OP side, back and plan views."""
import numpy as np
import shapely
from ridge_boots_author_surface import *
from ridge_boots_author_upper import lacing, open_upper

def dominant_parts():
    b=Boot()
    open_upper(b)
    # The medial and lateral quarter seam rises in a smooth forward arc.
    for side in (-1,1):
        s='medial' if side<0 else 'lateral'
        def cut(name,pts,mat='Suede',h=.23,thread=True):
            coords=[(side*t*5.5,z) for t,z in pts];p=poly(coords,.18)
            b.panel(s+'_'+name,mat,p,wrap_chart,h,h-.060,.43,.12)
            if thread:
                b.stitches(s+'_'+name+'_lockstitch',p,wrap_chart,h+.021,.15)
                if name in ('upper_eyestay','sweeping_ankle_quarter'):
                    b.stitches(s+'_'+name+'_inner_lockstitch',p,wrap_chart,h+.020,.37)
        cut('upper_eyestay',[(.42,16.4),(.38,23.8),(.47,25.8),(.62,26.9),(.93,27.11),(1.17,26.57),(1.34,25.59),(1.38,24.65),(1.28,22.90),(1.24,19.1),(1.30,17.),(1.47,16.25),(1.06,15.75),(.62,16.09)],h=.72)
        cut('sweeping_ankle_quarter',[(.38,15.9),(.51,17.03),(1.22,17.59),(1.77,17.15),(1.94,16.4),(2.20,13.85),(2.50,13.02),(3.04,12.45),(3.14,12.0),(3.14,8.4),(2.63,8.1),(2.18,8.9),(1.72,10.50),(1.17,12.23),(.79,13.46),(.38,14.22)],h=.69)
        cut('lower_scalloped_quarter',[(.40,8.12),(.35,9.25),(.50,10.43),(.36,11.95),(.47,13.52),(.75,13.83),(1.0,12.2),(1.32,11.37),(1.53,10.0),(1.87,9.4),(2.52,10.40),(2.94,11.0),(3.13,10.95),(3.13,3.15),(1.25,3.12),(.82,4.5),(.75,5.50),(.80,6.7),(.95,7.78),(.77,8.61),(.61,8.45)],h=.235)
        if side==1:
            maker_label(b)
        # Real cut-outs in the wrap reveal the textile and suede behind them.
        ch=side_chart(side)
        out=poly([(-7.90,3.0),(-7.86,8.75),(-7.24,10.65),(-6.45,10.11),(-4.70,8.11),(-2.76,7.12),(.45,9.24),(2.55,11.13),(3.75,10.88),(5.72,5.13),(6.39,4.55),(8.19,5.42),(10.38,7.94),(11.54,7.99),(13.70,4.37),(15.22,4.35),(16.53,5.43),(18.11,6.06),(19.10,5.64),(20.07,4.28),(21.30,4.00),(21.92,4.54),(22.12,3.30),(20.91,2.19),(16.90,1.75),(12.44,1.72),(8.4,1.66),(4.0,1.98),(1.2,2.20),(-2.00,1.85),(-6.75,1.80)],.34)
        windows=[
            [(-7.05,7.59),(-5.73,6.49),(-3.59,5.58),(-2.72,3.52),(-6.91,3.69)],
            [(-1.44,6.74),(2.14,9.28),(3.58,4.03),(2.23,3.79),(.15,3.81)],
            [(6.75,3.18),(10.55,6.72),(12.27,3.14)],
            [(15.66,2.96),(17.70,4.94),(18.31,4.91),(19.16,3.25)]]
        for hole in windows:out=out.difference(poly(hole,.21))
        # Two lower pads remain visible inside the open quarter frame.
        for j,pad in enumerate((
            [(-7.36,5.93),(-3.88,5.20),(-2.34,4.43),(-2.59,3.65),(-7.22,4.35)],
            [(-1.48,6.23),(3.54,5.02),(3.80,3.86),(1.82,3.88),(-.42,4.33)],
            [(7.02,3.92),(11.54,4.35),(12.32,3.30),(7.12,3.20)],
        )):
            b.panel(s+'_inset_midsole_pad_'+str(j),'Frame',poly(pad,.12),ch,.37,.25,.47,.12,crease=True)
        b.panel(s+'_one_piece_windowed_stabilizer','Frame',out,ch,.88,.60,.34,.22,crease=True)
        # Heel band, visible through the stabilizer window, follows the curved upper.
    # The toe overlay is one piece of suede across the nose. Its U-shaped
    # throat surrounds the exposed woven vamp, without a cut at the centre.
    path=[(-1.76,3.0),(-1.71,4.45),(-1.50,5.8),(-1.16,6.7),(-.94,7.8),
          (-.75,8.11),(-.56,7.78),(-.50,7.15),(-.36,6.49),(-.19,6.20),
          (0.,6.18),(.19,6.20),(.36,6.49),(.50,7.15),(.56,7.78),(.75,8.11),
          (.94,7.8),(1.16,6.7),(1.50,5.8),(1.71,4.45),(1.76,3.)]
    toe=poly([(a*5.5,z) for a,z in path],.16)
    b.panel('one_piece_suede_toebox','Suede',toe,wrap_chart,.31,.24,.31,.13)
    b.stitches('vamp_saddle_stitch',toe,wrap_chart,.325,.19)
    # A suede heel spine with a loop anchored at both ends.
    heel=poly([(math.pi*5.5-1.65,9.6),(math.pi*5.5+1.65,9.6),(math.pi*5.5+1.16,14.1),(math.pi*5.5-.92,14.1)],.22)
    b.panel('achilles_spine','Suede',heel,wrap_chart,.28,.08,.5)
    def loop(u,v):
        t=math.pi+(u-.5)*.40;z=18.00+3.60*v+1.6*np.sin(math.pi*v)
        lift=.54+1.77*np.sin(math.pi*v)**1.3
        return surf(t,z,lift)
    b.grid('woven_pull_loop','Textile',loop,7,28)
    b.grid('woven_pull_loop_back','Textile',lambda u,v:loop(1-u,v)-normal(math.pi+(1-u-.5)*.40,18.+3.60*v+1.6*np.sin(math.pi*v))*.11,7,28)
    for u in (0,1):b.tube('pull_loop_selvedge_'+str(u),'Thread',loop(np.full(28,u),np.linspace(0,1,28)),.043,5)
    def bumper(u,v):
        t=(u-.5)*1.9;tz=3.75+2.34*maxcos(t)**2
        return surf(t,2.48+(tz-2.48)*v,.46+.11*np.maximum(0,np.sin(np.pi*v))**.5)
    b.grid('curved_toe_protector','Frame',bumper,43,15)
    # Tapered striations are moulded into the slanted toe bumper.
    for i,height in enumerate((.44,.61,.78)):
        u=np.linspace(.15,.85,39);p=bumper(u,height+.055*np.sin(np.pi*u))
        t=(u-.5)*1.9; n=normal(t,np.full(len(t),4.));p+=n*.024
        b.tube('toe_cap_rib_'+str(i),'Frame',p,.059*(.3+.7*np.sin(np.pi*np.linspace(0,1,len(t)))),6)
    b.grid('molded_rear_counter','Frame',lambda u,v:surf(math.pi+(u-.5)*1.84,2.34+(6.45+1.14*np.cos((u-.5)*2*math.pi))*v,.41),39,20)
    lacing(b);outsole(b)
    return b
def maxcos(t):return np.clip(np.cos(t),0,1)
def maker_label(b):
    from matplotlib.font_manager import FontProperties
    from matplotlib.textpath import TextPath
    # Short woven label captured under the edge of the leather eyestay.
    x,z=7.13,21.45
    tag=poly([(x-.08,z-1.06),(x+.61,z-1.11),(x+.70,z+1.16),(x+.01,z+1.20)],.045)
    b.panel('ts01_quarter_woven_label','Lining',tag,wrap_chart,.75,.70,.18,.04)
    loops=TextPath((0,0),'TS01',size=1,prop=FontProperties(fname='C:/Windows/Fonts/arialbd.ttf')).to_polygons()
    ink=None
    for ring in loops:
        part=Polygon(ring)
        ink=part if ink is None else ink.symmetric_difference(part)
    xmin,ymin,xmax,ymax=ink.bounds
    for j,part in enumerate(shapely.get_parts(ink)):
        if part.area<.001:continue
        def mapped(ring):
            q=np.asarray(ring.coords)
            return arr(x+.15+(q[:,1]-ymin)*.27/(ymax-ymin),
                       z+.77-(q[:,0]-xmin)*1.52/(xmax-xmin))
        glyph=Polygon(mapped(part.exterior),[mapped(r) for r in part.interiors])
        b.panel('ts01_label_woven_mark_'+str(j),'Thread',glyph,wrap_chart,.772,.770,.08,.01)
def rocker(x,y):
    toe=1.33*ease((y-15.8)/6.9)
    heel=.30*ease((-6.15-y)/2.2)
    arch=(.93+.48*ease((-x+1.)/5.0))*ease((y-.66)/1.70)*(1-ease((y-3.25)/3.9))
    return toe+heel+arch
def footprint(t):
    p=last(t,np.full_like(t,2.94));p[...,0]*=1.049;p[...,1]=7.2+(p[...,1]-7.2)*1.023
    return p[...,:2]
def outsole(b):
    def shell(u,v,heights,radii):
        t=u*TAU;xy=footprint(t);x,y=xy[...,0],xy[...,1]
        r=np.interp(v,np.linspace(0,1,len(radii)),radii)
        z=np.interp(v,np.linspace(0,1,len(heights)),heights)
        return arr(x*r,7.2+(y-7.2)*r,z+rocker(x,y)*(1.-.38*v))
    # Softer sidewall and grippier contact layer have separate tooling radii.
    b.grid('shock_absorbing_midsole','Frame',lambda u,v:shell(u,v,[1.36,1.47,1.75,2.60,2.90,3.13],[.978,1.004,1.016,1.016,1.005,.969]),101,13)
    b.grid('continuous_outsole_wall','Outsole',lambda u,v:shell(u,v,[.63,.75,.91,1.18,1.40,1.49],[.968,1.,1.015,1.018,1.007,.986]),101,12)
    perimeter=Polygon(footprint(np.linspace(0,TAU,120,endpoint=False)))
    def base(q,h):
        x,y=q.T;return arr(x,y,rocker(x,y)+.72-h)
    b.panel('outsole_recessed_tread_bed','Outsole',perimeter.buffer(-.09),base,.045,.015,1.05)
    from ridge_boots_tread import tread_blocks
    tread_blocks(b, perimeter, base)
