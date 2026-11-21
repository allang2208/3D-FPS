"""Two-storey portcullis housing. Local +Y faces the courtyard, all dimensions are cm."""
import math


def make_gallery_portal(west):
    from author_kit import new_mesh, box, field_courses, arch_curve, crown, hoist
    from source_mesh import save_role
    half,peak,top=(430.,480.,1050.) if west else (330.,460.,1010.)
    outer=half+104.
    m=new_mesh(3853 if west else 3857)
    cap=top-70.
    central=half*.30
    arc=lambda x:float(arch_curve(x,half,peak))

    def floor_z(x):
        # Level landings at the wall ends. At the middle the station broadens
        # into a level guard post above the road's original clear arch.
        if abs(x)>=half:return 360.
        if abs(x)<=central:return peak+32.
        t=(abs(x)-central)/(half-central)
        return arc(x)+20.+(1.-t)*(peak+12.-arc(central))

    def span(x0,x1,y0,y1,lo0,lo1,hi0,hi1,mat):
        m.solid([[(x0,y0,lo0),(x1,y0,lo1),(x1,y1,lo1),(x0,y1,lo0)],
                 [(x0,y0,hi0),(x1,y0,hi1),(x1,y1,hi1),(x0,y1,hi0)]],mat)

    def leaning_hull(x0,x1,y0,y1,z0,z1,thickness):
        pitch=math.atan2(z1-z0,x1-x0)
        # The top face is the exact walking plane. Rotating about its centre
        # would leave half the thickness above the intended wearing surface.
        offset=thickness*.5
        m.boxes.append(dict(center=[(x0+x1)*.5+offset*math.sin(pitch),(y0+y1)*.5,
                                    (z0+z1)*.5-offset*math.cos(pitch)],
                            size=[math.hypot(x1-x0,z1-z0),y1-y0,thickness],
                            pitch=math.degrees(pitch)))

    def bricks(x0,x1,y0,y1,z0,z1):
        if x1>x0 and z1>z0:field_courses(m,x0,x1,y0,y1,z0,z1)

    # The outer elevation and protected hoist slit keep their full original
    # height. On the inside the upper wall now bears on two piers over an open
    # gallery instead of filling the chamber with one solid collision block.
    joints={-half,half,-central,central,0.}
    joints.update(-half+i*(2*half/32.) for i in range(1,32))
    xs=sorted(joints)
    for a,b in zip(xs,xs[1:]):
        za,zb=arc(a),arc(b)
        for y0,y1 in ((-115.,-15.),(15.,40.)):
            span(a,b,y0,y1,za,zb,cap,cap,'Mortar')
            m.collision(a,b,y0,y1,max(za,zb),cap)
        fa,fb=floor_z(a),floor_z(b)
        span(a,b,40.,133.,za,zb,fa-10.,fb-10.,'Mortar')
        if min(fa,fb)-10.>max(za,zb):m.collision(a,b,40.,133.,max(za,zb),min(fa,fb)-10.)

    for side in (-1,1):
        l,r=sorted((side*half,side*outer))
        # A breast-high pier at the entrance to each wall walk, with a clear
        # person-height opening; the front face still reads as a continuous tower.
        box(m,l,r,-115,-91,-20,cap,'Mortar',True)
        box(m,l,r,-91,-15,-20,356,'Mortar',True)
        box(m,l,r,15,140,-20,356,'Mortar',True)
        c,d=sorted((side*(half+12),side*outer))
        box(m,c,d,-15,15,-20,356,'Mortar',True)
        box(m,l,r,-91,115,697,cap,'Mortar',True)
        bricks(l,r,-120,-113,0,cap)
        bricks(l,r,138,143,0,338)

    # Narrow portal reveals, wedge-shaped voussoirs and a projecting keystone.
    # The underside never intrudes into the existing arch or grille travel.
    radius=(half**2+(peak-340.)**2)/(2*(peak-340.))
    spring=peak-radius
    alpha=math.asin(half/radius)
    n=25 if west else 21
    for side in (-1,1):
        face=-134 if side<0 else 138
        for i in range(n):
            t0=-alpha+2*alpha*i/n+.0009
            t1=-alpha+2*alpha*(i+1)/n-.0009
            key=i==n//2
            h=36. if key else 28.
            edge=face+side*(11 if key else 6)
            y0,y1=sorted((face-side*21,edge))
            # Rear blocks finish at the wearing surface. Their upper backs
            # are bedded inside the gallery instead of projecting into it.
            def coord(t,r,upper):
                x=r*math.sin(t);z=spring+r*math.cos(t)
                if upper and side>0:z=min(z,floor_z(x)-1.5)
                return x,z
            x0,z0=coord(t0,radius,False)
            x1,z1=coord(t1,radius,False)
            xa,za=coord(t0,radius+h,True)
            xb,zb=coord(t1,radius+h,True)
            m.solid([[(x0,y0,z0),(x1,y0,z1),(x1,y1,z1),(x0,y1,z0)],
                     [(xa,y0,za),(xb,y0,zb),(xb,y1,zb),(xa,y1,za)]],'YardCap')
        for s in (-1,1):
            a,b=sorted((s*half,s*(half+48)))
            for row in range(12):
                base=row*340./12.
                m.stone(a,b,face-12,face+12,base+.4,base+340./12.-.4,'YardCap')
    bricks(-outer,outer,-120,-115,peak+39,cap)
    bricks(-half,half,40,45,peak+49,cap)
    box(m,-outer,outer,96,117,top-255,cap,'Mortar',True)
    bricks(-outer,outer,114,120,top-249,cap)
    box(m,-outer,outer,89,128,top-266,top-253,'YardCap',True)

    deck=sorted(set([-outer,outer]+xs))
    for a,b in zip(deck,deck[1:]):
        shoulder=(a+b)*.5
        y0=-89. if abs(shoulder)>half else 41.
        y1=264.
        za,zb=floor_z(a),floor_z(b)
        span(a,b,y0,y1,za-15.,zb-15.,za-.85,zb-.85,'Mortar')
        leaning_hull(a,b,y0,y1,za,zb,13.)
        # A scored stone wearing course. Its flush joints are decorative,
        # while an unbroken collision face supports the full-width walk.
        for i in range(3):
            y=y0+(y1-y0)*i/3.
            span(a+.12,b-.12,y+.20,y0+(y1-y0)*(i+1)/3.-.20,za-1.6,zb-1.6,za,zb,'YardCap')
        # Rear parapet leaves a real doorway on each stationary landing.
        if abs(shoulder)<half:
            span(a,b,y1-14,y1,za,zb,za+55,zb+55,'YardField')
            span(a,b,y1-16,y1+1,za+55,zb+55,za+61,zb+61,'YardCap')
            leaning_hull(a,b,y1-14,y1,za+61,zb+61,55*math.cos(math.atan2(zb-za,b-a)))
    # Stone corbels return the projecting ledge to the rear face. All supports
    # in the vehicle passage stay above its original curved clearance.
    for x in (-half*.82,-half*.46,0.,half*.46,half*.82):
        bottom=max(arc(x-11),arc(x+11))+.8
        roof=min(floor_z(x-11),floor_z(x+11))-7.
        if roof-bottom>4:
            box(m,x-10,x+10,137,195,bottom,roof,'YardField')
    # Keep the small level lookout used by existing player-docked stairs
    # and wall returns. The ground underneath is now completely clear.
    box(m,outer,outer+145.,63.,167.,346.,357.,'Mortar')
    for i in range(3):
        a=outer+145.*i/3.;b=outer+145.*(i+1)/3.
        box(m,a+.3,b-.3,63.4,166.6,357.,359.5,'YardCap')
    m.collision(outer,outer+145.,63.,167.,346.,360.)
    # The two side galleries have working clearances above the original rampart.
    # The high coping still spans the hoist crown at the original elevation.
    box(m,-outer,outer,-127,127,top-45,top-37,'YardCap',True)
    crown(m,outer,top)
    hoist(m,half,top)
    save_role('SM_HighPortalGallery'+('West' if west else 'East'),{},m)
