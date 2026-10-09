"""One dimensional contract for flights, landings, gallery openings and continuous guards."""
import math

KINDS={'Steps','Nosings','StairSupport','Landings','StairPiers','Rails','GalleryFascia'}
def build(g):
    g.ROOM='Hall'
    def box(k,c,s,m,col=False):g.box(k,c,s,m,collision=col)
    # Fascia is trimmed out of both stair mouths, instead of crossing the last tread.
    for a,b in ((-18,-17.50),(-14.30,14.30),(17.50,18)):
        box('GalleryFascia',(-15.96,(a+b)/2,4.03),(.08,b-a,.40),'Teal')
    def guard(path,foot=None):
        for height,mat,r in ((1.08,'Yellow',.032),(.50,'Steel',.022)):
            g.tube('Rails',[(x,y,z+height) for x,y,z in path],r,mat,20)
        posts={}
        for a,b in zip(path,path[1:]):
            length=math.dist(a,b);count=max(1,math.ceil(length/1.2))
            for i in range(count+1):
                t=i/count;p=tuple(a[j]+(b[j]-a[j])*t for j in range(3));posts[tuple(round(v,4) for v in p)]=p
            # Continuous shallow guard collision, with the project's traversal tag at import.
            dx=b[0]-a[0];dy=b[1]-a[1];ln=math.hypot(dx,dy);sx=-dy/ln*.04;sy=dx/ln*.04
            vs=[(p[0]+sign*sx,p[1]+sign*sy,p[2]+z) for p in (a,b) for sign,z in ((-1,0),(1,0),(1,1.115),(-1,1.115))]
            g.hull('Rails',vs,g.FACES)
        for x,y,z in posts.values():
            bottom=foot(x) if foot else z;height=z+1.08-bottom
            box('Rails',(x,y,bottom+height/2),(.056,.056,height),'Paint')
            box('Rails',(x,y,bottom+.014),(.13,.13,.028),'Steel')
    guard([(-16,-14.40,4.2),(-16,14.40,4.2)])
    going=4.7/14;rise=.15
    for side in (-1,1):
        yc=side*15.9
        for x0,z0 in ((-5,0),(-11.3,2.1)):
            x1=x0-14*going;z1=z0+2.1
            # Solid stair section follows every riser. Stone tops sit in recesses, not on a
            # second sloping skin that can poke through the final landing/tread surfaces.
            outline=[(x0,z0-.26),(x1,z1-.26),(x1,z1-.042)]
            for i in reversed(range(14)):
                top=z0+(i+1)*rise-.042;front=x0-i*going
                outline.append((front,top))
                if i:outline.append((front,z0+i*rise-.042))
                mid=x0-(i+.5)*going
                box('Steps',(mid,yc,z0+(i+1)*rise-.020),(going,3.16,.040),'Stone',True)
                box('Nosings',(front-.026,yc,z0+(i+1)*rise+.004),(.048,3.12,.008),'Dark')
            n=len(outline);vs=[(x,y,z) for y in (yc-1.58,yc+1.58) for x,z in outline]
            fs=[tuple(reversed(range(n))),tuple(n+i for i in range(n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
            g.poly('StairSupport',vs,fs,'Concrete')
            # Individual tread UCX boxes above are the walking support; a low ramp hull
            # fills the underside without introducing a convex cap over the treads.
            hv=[(x,y,z) for y in (yc-1.58,yc+1.58) for x,z in ((x0,z0-.26),(x1,z1-.26),(x1,z1-.06),(x0,z0+.09))]
            g.hull('StairSupport',hv,g.FACES)
        box('Landings',(-10.5,yc,1.97),(1.6,3.16,.26),'Stone',True)
        box('StairPiers',(-10.5,yc,.92),(.42,2.80,1.84),'Concrete',True)
        def stair_foot(x):
            if x>-5:return 0
            if x>-9.7:return min(2.1,(math.floor((-5-x+1e-8)/going)+1)*rise)
            if x>-11.3:return 2.1
            if x>-16:return 2.1+min(2.1,(math.floor((-11.3-x+1e-8)/going)+1)*rise)
            return 4.2
        for sy in (-1,1):
            y=yc+sy*1.50
            # The preceding floor/landing extends the rail slope by one going so both
            # rails meet at identical elevations without the former 15 cm vertical jump.
            guard([(-5+going,y,0),(-9.7+going,y,2.1),(-11.3+going,y,2.1),(-16+going,y,4.2),(-16,y,4.2)],stair_foot)
        guard([(-16,side*17.40,4.2),(-16,side*17.98,4.2)])
