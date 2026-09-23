"""Ceiling power distribution and pipe exposure masks, in room-local metres."""
import math
from mathutils import Vector

def install(H):
    H['PIPE_RUNS']=[]
    original=H['smooth_pipe']
    def pipe(points,radius):
        original(points,radius)
        ps=[Vector(p) for p in points]
        segments=[];flanges=[]
        for a,b in zip(ps,ps[1:]):
            d=b-a;n=d.normalized();segments.append((a,b,n,d.length,radius))
            if d.length>=.75:
                count=max(1,int(d.length/2.6))
                flanges.extend((a+d*((i+.5)/count),n,radius) for i in range(count))
        H['PIPE_RUNS'].append(dict(segments=segments,flanges=flanges))
    H['smooth_pipe']=pipe

def pipe_age(co,runs):
    nearest=None;distance=1e10
    for run in runs:
        for a,b,n,length,radius in run['segments']:
            t=max(0,min(length,(co-a).dot(n)));q=a+n*t
            dist=(co-q).length
            if dist<distance:distance=dist;nearest=(run,q,n,radius)
    if nearest is None:return .1,.12
    run,q,n,radius=nearest;radial=(co-q).normalized()
    underside=max(0,-radial.z) if abs(n.z)<.2 else .12
    seam=0;streak=0
    for p,axis,r in run['flanges']:
        axial=(co-p).dot(axis);rad=(co-p-axis*axial).length
        if rad>r+.23:continue
        seam=max(seam,math.exp(-abs(axial)/.065))
        if abs(axis.z)>.8 and .015<p.z-co.z<.60:
            theta=math.atan2(co.y-p.y,co.x-p.x)
            fingers=max(0,math.sin(theta*7.0+math.sin(theta*3.0)))**6
            streak=max(streak,fingers*math.exp(-(p.z-co.z)/.32))
    breakup=.78+.22*math.sin(co.x*8+co.y*9+co.z*5)**2
    grime=min(.75,.07+.23*underside+.34*seam+.26*streak)
    corrosion=min(.98,(.10+.22*underside+.74*seam+.60*streak)*breakup)
    return grime,corrosion

def construct(H,ibeam):
    box,tube,detail=H['box'],H['tube'],H['detail']
    routes=[];trays=[]
    def cable(label,segments,radius=.014):
        points=[]
        for controls in segments:
            p0,p1,p2,p3=map(Vector,controls)
            count=max(12,math.ceil(sum((b-a).length for a,b in zip((p0,p1,p2),(p1,p2,p3)))/.075))
            for i in range(count+1):
                if points and i==0:continue
                t=i/count;points.append((1-t)**3*p0+3*(1-t)**2*t*p1+3*(1-t)*t*t*p2+t**3*p3)
        # Dense cubic samples and parallel-transport rings preserve smooth bend tangents.
        tube('CableRoutes',points,radius,'BossCableJacket',16)
        routes.append(dict(label=label,radius_m=radius,control_segments=segments))
        return points
    def tie(center,axis,r=.040):
        detail.ring(center,axis,r+.002,r,.009,'BossCableJacket',20,'CableRoutes')
    def tray(label,a,b,width=.42):
        a,b=Vector(a),Vector(b);axis=(b-a).normalized();side=Vector((-axis.y,axis.x,0));z=a.z
        for sign in (-1,1):
            p=a+side*sign*width/2;end=b+side*sign*width/2
            ibeam('CableTrays',p,end,.025,.07,.004,'BossStructuralSteel')
        count=max(1,math.ceil((b-a).length/.32))
        for i in range(count+1):
            p=a+(b-a)*i/count
            ibeam('CableTrays',p-side*width/2-Vector((0,0,.022)),p+side*width/2-Vector((0,0,.022)),.025,.022,.004,'BareSteel')
        count=max(1,math.ceil((b-a).length/1.5))
        for i in range(count+1):
            p=a+(b-a)*i/count
            for sign in (-1,1):
                foot=p+side*sign*(width/2+.045)
                tube('CableTrays',[foot,Vector((foot.x,foot.y,8.38))],.007,'BareSteel',12)
                box('CableTrays',(foot.x,foot.y,8.39),(.095,.095,.02),'BossStructuralSteel')
        trays.append(dict(label=label,a=list(a),b=list(b),width=width))
    # Main trays sit above the roof trusses (top 8.16 m), directly under the 8.4 m soffit.
    z=8.235
    for sign in (-1,1):
        x=sign*12.8
        tray('Ceiling main '+str(sign),(x,.55,z),(x,26.1,z),.46)
        for lane in range(5):
            xx=x+(lane-2)*.059;segments=[]
            for j in range(22):
                y0=.55+j*25.55/22;y1=.55+(j+1)*25.55/22
                segments.append([(xx,y0,z+.020),(xx+.004*math.sin(j+lane),y0+.32,z+.008),(xx-.004*math.sin(j+lane),y1-.32,z+.008),(xx,y1,z+.020)])
            cable('Ceiling main bundle %d/%d'%(sign,lane),segments,.015 if lane<3 else .011)
        for y in (2,5,8,11,14,17,20,23,25):
            box('CableRoutes',(x,y,z+.040),(.32,.010,.012),'BossCableJacket')
        # Cabinet feeds stay on the wall side of the water mains, clear of the pipes.
        for y in (9.5,18.3):
            end=sign*14.73
            tray('Wall cabinet branch',(x,y,z),(end,y,z),.18)
            cable('Wall cabinet feed',[
                [(x,y,z+.008),(sign*13.6,y,z+.008),(end,y,z+.01),(end,y,8.08)],
                [(end,y,8.08),(end,y,7.45),(end,y,6.20),(end,y,5.85)],
                [(end,y,5.85),(end,y,5.67),(sign*14.50,y,5.77),(sign*14.50,y,5.59)]],.012)
            for h in (7.65,6.90,6.12):
                box('CableTrays',(sign*14.765,y,h),(.11,.10,.075),'BossStructuralSteel')
                tie((end,y,h),(0,0,1),.014)
            detail.ring((sign*14.5,y,5.59),(0,0,1),.027,.012,.040,'BareSteel',24,'CableRoutes')
    for m in H['ROOM']['machines']:
        x,y,_=m['at'];sign=m['pipe_side'];feed_x=x-1.48;feed_y=y-.45
        tray(m['id']+' overhead supply',(sign*12.8,feed_y,z),(feed_x,feed_y,z),.22)
        # Cable turns down with a controlled radius and strain relief at both ends.
        cable(m['id']+' ceiling drop',[
            [(sign*12.8,feed_y,z+.022),(feed_x+sign*.65,feed_y,z+.022),(feed_x,feed_y,8.17),(feed_x,feed_y,7.88)],
            [(feed_x,feed_y,7.88),(feed_x,feed_y,6.90),(feed_x-sign*.18,feed_y+.10,5.10),(feed_x-sign*.16,feed_y+.10,4.20)],
            [(feed_x-sign*.16,feed_y+.10,4.20),(feed_x-sign*.14,feed_y+.10,3.30),(feed_x,feed_y,2.30),(feed_x,feed_y,1.60)]],.018)
        for h in (7.89,1.58):
            detail.ring((feed_x,feed_y,h),(0,0,1),.037,.018,.11,'BossCableJacket',24,'CableRoutes')
        tube('CableRoutes',[(feed_x,feed_y,1.465),(feed_x,feed_y,1.575)],.025,'BareSteel',24)
        # Local motor lead stays above the base, with a broad service loop instead of floor bends.
        cable(m['id']+' flexible motor lead',[
            [(x-1.33,y-.34,1.34),(x-1.05,y-.34,1.34),(x-1.05,y-1.36,1.05),(x-.87,y-1.36,1.48)],
            [(x-.87,y-1.36,1.48),(x-.69,y-1.36,1.91),(x-.74,y-1.00,2.15),(x-.30,y-1.00,2.15)]],.015)
        detail.ring((x-1.33,y-.34,1.34),(1,0,0),.029,.015,.07,'BareSteel',24,'CableRoutes')
    H['CABLE_LAYOUT']=dict(ceiling_tray_level_m=z,soffit_m=8.4,roof_truss_top_m=8.16,
        trays=trays,cables=routes,notes='Cubic cable curves; ceiling distribution; strain-relieved cabinet and motor feeds; no floor loop')
