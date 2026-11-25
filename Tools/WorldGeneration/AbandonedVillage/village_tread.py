"""Metric traffic and shelter fields for the main street and chapel ground material."""
import math

import numpy as np


def ramp(value):
    t = np.clip(value, 0., 1.)
    return t*t*(3.-2.*t)


def window(x, y, bounds):
    left, bottom, right, top = bounds
    xs = slice(*np.searchsorted(x[0], [left, right]))
    ys = slice(*np.searchsorted(y[:, 0], [bottom, top]))
    return (ys, xs), x[:, xs].astype('f'), y[ys].astype('f')


def soil_variation(x, y, scale, seed):
    """Smooth metric noise; both street banks sample the same ground field in XY."""
    qx, qy = x/scale, y/scale
    ix, iy = np.floor(qx).astype(int), np.floor(qy).astype(int)
    # Offsets at adjacent grid corners must come from the same noise lattice.
    ix, iy = ix-ix.min(), iy-iy.min()
    lattice = np.random.default_rng(seed).uniform(-1.,1.,(iy.max()+2, ix.max()+2)).astype('f')
    tx, ty = ramp(qx-np.floor(qx)), ramp(qy-np.floor(qy))
    south = lattice[iy,ix]*(1.-tx)+lattice[iy,ix+1]*tx
    north = lattice[iy+1,ix]*(1.-tx)+lattice[iy+1,ix+1]*tx
    return south*(1.-ty)+north*ty


def tread(x, y, points, displacement=0.):
    """Distance to a foot line, with separately authored widths at each station."""
    field = np.full((y.shape[0],x.shape[1]), -100., dtype='f')
    for a,b in zip(points,points[1:]):
        dx,dy = b[0]-a[0],b[1]-a[1]
        length = math.hypot(dx,dy)
        if length < .015:
            continue
        t = np.clip(((x-a[0])*dx+(y-a[1])*dy)/(length*length),0.,1.)
        distance = np.hypot(x-(a[0]+dx*t)-dy/length*displacement,
                            y-(a[1]+dy*t)+dx/length*displacement)
        field = np.maximum(field,a[2]+(b[2]-a[2])*t-distance)
    return field


def street_wear(x, y, main, roads, cart_distance, fine):
    points = main['points']
    reach = main['width']*.5+3.25
    bounds = (min(p[0] for p in points)-reach,min(p[1] for p in points)-reach,
              max(p[0] for p in points)+reach,max(p[1] for p in points)+reach)
    index, x, y = window(x,y,bounds)
    dist = cart_distance[index]
    coarse = soil_variation(x,y,4.35,213)
    middle = soil_variation(x,y,1.37,837)
    fine = fine[index]
    # Each narrower approach brings footsteps from its own direction. A doorway
    # on one bank can widen that shoulder without scuffing the opposite one.
    approaches = np.zeros_like(dist,dtype='f')
    for line,width in roads:
        if width>=main['width']:
            continue
        field = tread(x,y,[(*p,width*.5) for p in line])
        approaches = np.maximum(approaches,ramp((field+1.28)/1.48))
    shoulder = main['width']*.5+.64*coarse+.20*middle+.80*approaches-dist
    pressure = ramp((shoulder+.62+.36*fine)/1.36)
    wheel = np.exp(-((dist-(.86+.14*middle))/(.32+.07*(coarse+1.)))**2)
    # Gravel shows through discontinuously at firm wheel landings and where
    # carts turn. Elsewhere even the centre can retain its finer packed soil.
    gravel = np.clip(.22+.44*wheel+.28*approaches+.46*coarse+.27*middle+.20*fine,0.,1.)
    gravel_edge = np.maximum(-shoulder+.32,1.29-2.43*gravel)
    strength = np.clip(.69+.26*gravel+.05*fine,0.,1.)
    earth = pressure*np.clip(.68+.23*wheel+.18*approaches+.14*middle+.12*fine,.28,1.)
    # Faint interrupted turf survives between wheel tracks, especially away
    # from doors and forks. Never cut the travelling surface across both wheels.
    turf = ramp((.74-dist+.13*middle)/.52)*ramp((.32-coarse+.36*middle)/.85)*(1.-approaches)
    earth *= 1.-.80*turf
    gravel_edge = np.maximum(gravel_edge,1.62*turf-.48)
    # Return smoothly to the existing terrain on the outer approaches at either gate.
    town = ramp((x-points[0][0]+1.7)/3.3)*ramp((points[-1][0]-x+1.7)/3.3)
    blend = town*ramp((reach-dist)/1.05)
    return index,blend,gravel_edge,strength,earth


def chapel_wear(x, y, chapel, fine):
    cx,cy = chapel['center']
    front,back,side,_ = chapel['yard']
    index,x,y = window(x,y,(cx+front-2.,cy-side-1.,cx+back+1.,cy+side+1.))
    x,y = x-cx,y-cy
    coarse = soil_variation(x,y,3.6,2607)
    mid = soil_variation(x,y,1.10,533)
    fine = fine[index]
    drift = .19*coarse+.095*mid
    # Local metres from the chapel origin, aligned to the runtime west stairs,
    # pew front and visitor side of the three headstones. The wider landings at
    # each approach dissipate into narrower, partly regrown foot trails.
    entry = tread(x,y,[(front,0.,.98),(-18.4,.22,.77),(-14.6,-.14,.83),(-11.42,0.,1.28)],drift)
    seat = tread(x,y,[(-14.3,-.25,.58),(-12.46,-1.50,.46),(-11.58,-2.76,.62),
                      (-11.40,-4.43,.44)],drift*.6)
    graves = tread(x,y,[(-18.50,0.,.48),(-16.69,4.50,.50),(-12.88,8.50,.64),
                        (-9.75,9.75,.55),(-6.84,9.96,.44),(-2.53,10.16,.25)],drift)
    # Leave narrow tongues of turf toward the lesser-used far end of the burial walk.
    visit = np.maximum(np.maximum(entry,seat-.16),graves-.19+.19*coarse)
    edge = .32*mid+.29*fine
    walked = ramp((visit+.63+edge)/1.18)
    worn_soil = walked*np.clip(.77+.14*mid+.10*coarse+.20*fine,.45,1.)

    bounds = np.minimum(np.minimum(x-front,back-x),side-np.abs(y))
    nave = np.maximum(np.abs(x)-10.2,np.abs(y)-5.25)
    wall = np.minimum(bounds,nave)
    # Protected returns collect damp earth under the grass. Separate outcrops
    # break through this bank; their apron disappears before the visitor line.
    shelter = ramp((1.15+.95*coarse+.43*mid-wall)/1.28)*ramp((wall+.35)/.56)
    soil = np.maximum(worn_soil,shelter*np.clip(.47+.33*coarse+.22*mid,0.,.86))
    # Stone is a minority in a walked churchyard. Reveal it at the seating
    # turn, gate and stair landing, and in occasional eroded wall toes.
    junction = np.maximum(ramp((np.minimum(entry,seat)+.72)/1.22),
                          ramp((np.minimum(entry,graves)+.75)/1.20))
    steps = ramp((1.9-np.hypot((x+11.50)*.90,y*.78))/1.25)
    exposed = walked*(.10+.27*junction+.35*steps+.27*mid+.26*coarse+.15*fine)
    exposed = np.maximum(exposed,shelter*np.clip(.16+.50*coarse+.27*mid,0.,.55))
    gravel_edge = np.clip(1.44-2.20*exposed+1.06*(1.-ramp(exposed/.24)),-.48,2.5)
    return index,soil*ramp((bounds+.35)/.45),gravel_edge


def protected_turf(x,y,plan,cart_distance,roads,noise,wall_segments,street_patch,church_patch,church_soil):
    """Ground cover lengthens from protected masonry into the unwalked shoulder."""
    field = np.zeros_like(noise,dtype='f')
    ys,xs=street_patch
    X,Y=x[:,xs],y[ys]
    broad=soil_variation(X,Y,5.2,932)
    mid=soil_variation(X,Y,1.52,674)
    grain=noise[street_patch]
    foot=np.full_like(broad,50.)
    def wall(a,b,half):
        dx,dy=b[0]-a[0],b[1]-a[1]
        t=np.clip(((X-a[0])*dx+(Y-a[1])*dy)/max(.001,dx*dx+dy*dy),0.,1.)
        np.minimum(foot,np.hypot(X-a[0]-t*dx,Y-a[1]-t*dy)-half,out=foot)
    for p,w in wall_segments(plan):
        wall(p[1:3],p[3:5],w)
    cx,cy=plan['chapel']['center']
    front,back,side,_=plan['chapel']['yard']
    # This long boundary is assembled by the chapel at runtime, separate from the village wall kit.
    wall((cx+front,cy+side),(cx+back,cy+side),.24)
    outside=cart_distance[street_patch]-plan['roads'][0]['width']*.5
    depth=1.48+1.10*broad+.61*mid
    fringe=ramp((depth+.40-foot+.34*grain)/1.04)
    turf=fringe*ramp((outside+.26+.55*mid+.22*grain)/.92)
    turf*=ramp((4.75-outside)/1.1)*ramp((.91+broad+.64*mid)/.86)
    for line,width in roads:
        if width<plan['roads'][0]['width']:
            clearance=-tread(X,Y,[(*p,width*.48) for p in line])
            turf*=ramp((clearance+.08+.12*mid)/.72)
    field[street_patch]=turf*.98
    ys,xs=church_patch
    X,Y=x[:,xs]-cx,y[ys]-cy
    broad=soil_variation(X,Y,3.85,188)
    mid=soil_variation(X,Y,1.21,911)
    enclosure=np.minimum(np.minimum(X-front,back-X),side-np.abs(Y))
    nave=np.maximum(np.abs(X)-10.2,np.abs(Y)-5.25)
    edge=np.minimum(enclosure,nave)
    cover=ramp((3.35+1.8*broad+.72*mid-edge)/2.4)*ramp((.96+broad+.72*mid)/1.14)
    cover*=ramp((enclosure+.05)/.37)*ramp((nave+.20)/.49)*(1.-ramp((church_soil-.13)/.64))
    np.maximum(field[church_patch],cover*.91,out=field[church_patch])
    return field
