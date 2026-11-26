"""Workshop maker's wheel sign and reeved entrance hoist, in centimetres."""
import math

import numpy as np
from chapel_gatehouse import pin, spindle

OAK, IRON, BRASS, ROPE = "SignOak", "ForgedStrap", "WheelBrass", "HempCord"


def tube(mesh, points, radius, material, normal, closed=False, sides=8):
    """Sweep in a plane. Rope UVs follow its length, including the returns over each sheave."""
    path = np.asarray(points, dtype=float)
    normal = np.asarray(normal, dtype=float)
    rings = []
    lengths = [0.]
    for i, p in enumerate(path):
        prev = path[(i-1) % len(path)] if closed or i else p
        after = path[(i+1) % len(path)] if closed or i+1 < len(path) else p
        tangent = after-prev
        tangent /= np.linalg.norm(tangent)
        side = np.cross(tangent, normal)
        r = radius[i] if isinstance(radius, list) else radius
        rings.append([p+r*(math.cos(a)*normal+math.sin(a)*side)
                      for a in np.arange(sides)*math.tau/sides])
        if i:
            lengths.append(lengths[-1]+np.linalg.norm(path[i]-path[i-1]))
    for i in range(len(path) if closed else len(path)-1):
        j = (i+1) % len(path)
        v0 = lengths[i]/8.
        v1 = (lengths[i]+np.linalg.norm(path[j]-path[i]))/8.
        for k in range(sides):
            n = (k+1) % sides
            for verts, coords in (
                ((rings[i][k],rings[i][n],rings[j][n]), ((k/sides,v0),((k+1)/sides,v0),((k+1)/sides,v1))),
                ((rings[i][k],rings[j][n],rings[j][k]), ((k/sides,v0),((k+1)/sides,v1),(k/sides,v1)))):
                mesh.triangle(*verts,material)
                if material == ROPE:
                    mesh.groups[material]["uv0"][-3:] = list(coords)
    if not closed:
        for k in range(sides):
            n = (k+1) % sides
            mesh.triangle(path[0],rings[0][n],rings[0][k],material)
            mesh.triangle(path[-1],rings[-1][k],rings[-1][n],material)


def eye(m, x,y,z, width,height, plane, radius):
    angles = np.arange(16)*math.tau/16
    points = [(x+(width*math.cos(a) if plane=="xz" else 0),
               y+(width*math.cos(a) if plane=="yz" else 0),z+height*math.sin(a)) for a in angles]
    tube(m,points,radius,IRON,(0,1,0) if plane=="xz" else (1,0,0),closed=True)


def trade_sign(m):
    # Wall plate bolts into the front framing. A knee brace takes the cantilever back to the post.
    m.member((245,-584,252),(245,-584,299),13,4,IRON)
    for z in (256,294):
        for x in (241,249):
            pin(m,(x,-586,z),(0,-2,0),1.55,BRASS)
    m.member((245,-584,287),(245,-647,287),5,5,IRON)
    tube(m,[(245,-586,260),(245,-598,262),(245,-610,266),(245,-624,277),(245,-640,286)],
         2,IRON,(1,0,0))
    m.member((212,-643,287),(278,-643,287),5.5,5.5,IRON)
    for x in (218,272):
        eye(m,x,-643,282.8,2.4,4.0,"xz",1.0)
        eye(m,x,-643,276.5,2.3,4.4,"yz",1.0)
        eye(m,x,-643,269.6,2.4,4.3,"xz",1.0)
        m.member((x,-643,258),(x,-643,266),3.2,3.2,IRON)
    # Horizontal plank end grain and rolled edges remain visible around the wrapped iron straps.
    for z,half in ((221,37.5),(237.4,41),(253.8,39.5)):
        m.member((245-half,-643,z),(245+half,-643,z),6,16.15,OAK)
    for x in (218,272):
        for y in (-646.5,-639.5):
            m.member((x,y,215),(x,y,261),4.4,1.4,IRON)
            for z in (219,237,257):
                pin(m,(x,y+(-.72 if y<-643 else .72),z),(0,-1.2 if y<-643 else 1.2,0),1.3,BRASS)
        m.member((x,-647,261.6),(x,-639,261.6),4.4,1.4,IRON)
    # Cast wheel with twelve squared teeth, softened front rim and open space between its spokes.
    # Traverse inner/front to inner/back to outer/back to outer/front so the raised face faces the road.
    phases = [(i+f)*math.tau/12 for i in range(12) for f in (0.,.22,.34,.67,.79)]
    tops = [17.3,17.3,20.1,20.1,17.3]*12
    def contour(radii,y):
        return [(245+r*math.cos(a),y,237.4+r*math.sin(a)) for a,r in zip(phases,radii)]
    r0 = [13.4]*len(phases)
    m.rim([contour(r0,-650.1),contour(r0,-646.1),contour(tops,-646.1),contour(tops,-649.3),
           contour([r-.55 for r in tops],-650.1)], BRASS)
    for i in range(6):
        a = math.tau*i/6+math.pi/6
        m.member((245+4*math.cos(a),-648,237.4+4*math.sin(a)),
                 (245+14*math.cos(a),-648,237.4+14*math.sin(a)),2.8,3.1,BRASS)
    spindle(m,(245,-646,237.4),(245,-652.5,237.4),[(0,5.1),(.68,5.6),(1,4.1)],BRASS,16)
    pin(m,(245,-652.5,237.4),(0,-1.4,0),2.6,IRON)


def entrance_hoist(m):
    m.member((0,-476,388),(0,-699,388),20,25,OAK)
    m.member((0,-575,298),(0,-668,376),13,15,OAK)
    for y in (-602,-674):
        for x in (-10.6,10.6):
            m.member((x,y,355 if y==-674 else 375),(x,y,401),8.5,2.6,IRON)
            pin(m,(x,y,388),(math.copysign(2.4,x),0,0),2.4,BRASS)
        m.member((-11,y,400.7),(11,y,400.7),8.6,2.4,IRON)
    # Grooved head sheave, its axle and the two riveted cheeks of the travelling block.
    for x in (-11,11):
        m.member((x,-674,353),(x,-674,388),11,3.2,IRON)
        m.member((x,-674,280),(x,-674,305),10,3.2,OAK)
        pin(m,(x,-674,299),(math.copysign(3.1,x),0,0),3.6,BRASS)
    for z,r in ((353,15.5),(299,10)):
        spindle(m,(-8,-674,z),(8,-674,z),[(0,r+2.3),(.16,r+2.3),(.34,r),(.67,r),(.85,r+2.3),(1,r+2.3)],IRON,24)
        spindle(m,(-14,-674,z),(14,-674,z),[(0,3.2),(.10,3.6),(.9,3.6),(1,3.2)],BRASS,12)
    # Dead-end eye at the boom, around the lower pulley, over the upper one, back to the wall cleat.
    lower=[(0,-674+11.4*math.cos(a),299+11.4*math.sin(a)) for a in np.linspace(0,-math.pi,16)]
    upper=[(0,-674+16.9*math.cos(a),353+16.9*math.sin(a)) for a in np.linspace(math.pi,math.pi*.22,19)]
    eye(m,0,-662.6,373.1,3,4,"yz",1.35)
    tube(m,[(0,-662.6,370)]+lower+upper+[(0,-638,348),(0,-608,332),(0,-584,318)],
         1.45,ROPE,(1,0,0),sides=10)
    m.member((-5,-583,318),(5,-583,318),6,6,IRON)
    m.member((-11,-674,282),(11,-674,282),8,6,IRON)
    eye(m,0,-674,278,3,4.3,"xz",1.45)
    path=[(0,-674,275),(0,-674,270),(0,-677,267),(0,-678,261),(0,-676,257),(0,-671,256),
          (0,-667,258),(0,-665.6,261.5),(0,-665.8,264)]
    tube(m,path,[2.2,2.3,2.5,2.6,2.4,2.1,1.55,.9,.32],IRON,(1,0,0),sides=10)
