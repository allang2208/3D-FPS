"""Physical-scale tailoring fields shared by sculpting, baking and native fits.

Coordinates are in centimetres. Pattern geometry is authored, not inferred
from colour noise. Only the back-side envelope gains volume.
"""
import json
from pathlib import Path
import numpy as np

P = Path(__file__).resolve().parents[2]
R = P/'SourceAssets/BlackLeatherDetail20260928'
ANATOMY = P/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':'))+'\n', encoding='utf-8')


def unit(v):
    a = np.asarray(v, dtype=float)
    return a/np.maximum(np.linalg.norm(a, axis=-1, keepdims=True), 1.e-12)


def smooth(a, b, value):
    t = np.clip((value-a)/(b-a), 0., 1.)
    return t*t*(3.-2.*t)


def gauss(value, center, width):
    return np.exp(-((value-center)/width)**2)


def matrix(bone):
    out = np.eye(4)
    out[:3, :3] = np.asarray(bone['axes']).T
    out[:3, 3] = bone['position']
    return out


def frame(bones, anatomy, side):
    wrist = np.asarray(bones['hand_'+side]['position'])
    z = unit(anatomy[side]['dorsal'])
    y = np.asarray(bones['middle_01_'+side]['position'])-wrist
    y = unit(y-z*(y@z))
    x = np.cross(y, z)*(1 if side == 'r' else -1)
    return np.asarray([x, y, z]), wrist


def polyline(x, y, points):
    distance = np.full_like(x, 1.e6)
    arc = np.zeros_like(x)
    accumulated = 0.
    for p0, p1 in zip(points[:-1], points[1:]):
        a, b = np.asarray(p0), np.asarray(p1)
        ab = b-a
        length = float(np.linalg.norm(ab))
        t = np.clip(((x-a[0])*ab[0]+(y-a[1])*ab[1])/(length*length), 0., 1.)
        d = np.hypot(x-a[0]-t*ab[0], y-a[1]-t*ab[1])
        pick = d < distance
        arc = np.where(pick, accumulated+t*length, arc)
        distance = np.minimum(distance, d)
        accumulated += length
    return distance, arc


def rectangle(x, y, cx, cy, hx, hy, radius):
    a, b = np.abs(x-cx)-hx+radius, np.abs(y-cy)-hy+radius
    return np.hypot(np.maximum(a, 0), np.maximum(b, 0))+np.minimum(np.maximum(a,b),0)-radius


def back_pattern(x, y):
    """Soft dorsal panels, double lock stitches, wrist binding and woven crest."""
    shape = ((np.abs((x+.55)/3.48))**4+(np.abs((y-4.55)/3.35))**4)**.25
    signed = (shape-1)*3.3
    panel = 1-smooth(-.07, .08, signed)
    plateau = 1-smooth(-.45, -.05, signed)
    low = .075*plateau
    rim = gauss(signed,-.055,.045)
    seam = gauss(signed,-.22,.026)+gauss(signed,-.40,.025)
    # Elliptic seam arc is continuous around the main panel.
    phase = np.arctan2((y-4.55)/3.35, (x+.55)/3.48)*3.4
    dash = 1-smooth(.066,.092,np.abs(np.mod(phase,.25)-.125))
    thread = np.clip(seam*dash,0,1)
    fine = .026*rim+.011*thread-.008*seam
    crease = np.zeros_like(x)
    # Curved construction channels distinguish the back panel from knuckle pads.
    for line in [[(-3.55,2.1),(-2.85,4.3),(-2.2,6.8)],
                 [(2.4,2.1),(1.8,4.3),(1.2,6.8)],
                 [(-2.8,6.95),(-1.1,7.50),(.5,7.55),(1.9,7.10)]]:
        dist, arc = polyline(x,y,line)
        groove = gauss(dist,0,.060)
        crease = np.maximum(crease,groove)
        fine -= .017*groove
        stitch = gauss(dist,.17,.028)*(1-smooth(.065,.10,np.abs(np.mod(arc,.27)-.135)))
        thread = np.maximum(thread,stitch)
        fine += .010*stitch
    # A flexible wrist closure, wholly inside the unchanged cuff boundary.
    sd = rectangle(x,y,-.25,-1.28,3.10,.85,.28)
    strap = 1-smooth(-.04,.04,sd)
    low += .070*(1-smooth(-.32,-.04,sd))
    border = gauss(sd,-.11,.036)
    seam_phase = x+2*y
    thread = np.maximum(thread,border*(1-smooth(.06,.095,np.abs(np.mod(seam_phase,.25)-.125))))
    fine += .016*border
    # Small fabric label: restrained warm stitching, original abstract crest.
    label_sd = rectangle(x,y,-.55,2.45,.83,.75,.17)
    label = 1-smooth(-.03,.04,label_sd)
    low += .027*label
    label_edge = gauss(label_sd,-.065,.025)
    thread = np.maximum(thread,label_edge*.85)
    crest = np.zeros_like(x)
    for line in [[(-.98,2.18),(-.55,2.76),(-.12,2.18)],
                 [(-.87,2.07),(-.55,2.48),(-.23,2.07)],
                 [(-.99,2.88),(-.11,2.88)]]:
        dist,_ = polyline(x,y,line)
        crest = np.maximum(crest,gauss(dist,0,.043))
    crest *= label
    fine += .017*crest
    # Broad wrinkles radiate from the wrist; avoid uniformly noisy embossing.
    folds = gauss(y, .70+.20*np.sin(x*1.8), .09)*gauss(x,0,2.7)
    folds += gauss(y, .30+.16*np.sin(x*2.1), .075)*gauss(x,.2,2.4)
    fine -= .012*folds
    wear = np.clip(.45*rim+.5*crease+.35*border+.24*folds,0,1)
    return dict(low=low, fine=fine, thread=np.clip(thread,0,1), panel=panel,
                cloth=np.maximum(label,strap*.72), crest=crest, wear=wear,
                cavity=np.clip(seam*.18+crease*.25+folds*.20,0,.45))


def palm_pattern(x,y):
    panel_sd=rectangle(x,y,-1.05,4.75,2.65,2.65,.80)
    panel=1-smooth(-.05,.05,panel_sd)
    seam=gauss(panel_sd,-.15,.036)
    phase=np.arctan2(y-4.75,x+1.05)*2.65
    stitch=seam*(1-smooth(.07,.095,np.abs(np.mod(phase,.27)-.135)))
    crease=np.zeros_like(x)
    for line in [[(2.3,2.0),(1.45,3.1),(.1,4.05),(-2.4,4.25)],
                 [(2.6,2.35),(1.8,4.35),(1.0,6.2)],
                 [(-3.0,6.55),(-1.6,6.10),(.3,6.2),(1.7,6.8)]]:
        distance,_=polyline(x,y,line)
        crease=np.maximum(crease,gauss(distance,0,.065))
    fine=.010*stitch-.020*crease-.007*seam
    return dict(panel=panel,thread=stitch,crease=crease,fine=fine)


def design_fields(points, normals, weights, bones, anatomy):
    count = len(points)
    design = np.zeros((count,2))
    back = np.zeros(count)
    digit = np.zeros(count)
    digit_t = np.zeros(count)
    finger_pad = np.zeros(count)
    finger_arc = np.zeros(count)
    finger_seam = np.full(count,3.)
    for side in ('l','r'):
        ids = np.array([i for i,w in enumerate(weights) if sum(v for n,v in w.items() if n.endswith('_'+side))>.5],dtype=int)
        if not len(ids):
            continue
        f,wrist = frame(bones,anatomy,side)
        coords = (points[ids]-wrist)@f.T
        design[ids] = coords[:,:2]
        dorsal = np.tile(f[2],(len(ids),1))
        total = np.zeros(len(ids))
        dt = np.zeros(len(ids))
        pad = np.zeros(len(ids))
        arc = np.zeros(len(ids))
        seam_distance = np.zeros(len(ids))
        for spec in anatomy[side]['digits']:
            name = spec['bone']
            mass = np.array([weights[i].get(name,0) for i in ids])
            if mass.max()<1.e-7:
                continue
            total += mass
            head = np.array(spec['head'])
            axis = np.array(spec['axis'])
            t = (points[ids]-head)@axis/spec['length']
            dt += mass*t
            dorsal += mass[:,None]*(np.array(spec['dorsal'])-f[2])
            pad += mass*gauss(t,.48,.24)*(.060 if spec['segment']==1 else .032)
            previous=sum(s['length'] for s in anatomy[side]['digits']
                         if s['digit']==spec['digit'] and s['segment']<spec['segment'])
            arc+=mass*(t*spec['length']+previous)
            relative=points[ids]-head-(t*spec['length'])[:,None]*axis
            angle=np.arctan2(relative@np.array(spec['across']),relative@np.array(spec['dorsal']))
            seam_distance+=mass*(np.abs(angle)-1.04)*spec['radius']
        back[ids] = smooth(.12,.68,(unit(dorsal)*normals[ids]).sum(1))
        digit[ids] = np.clip(total,0,1)
        digit_t[ids] = dt/np.maximum(total,1.e-7)
        finger_pad[ids] = pad
        finger_arc[ids]=arc/np.maximum(total,1.e-7)
        finger_seam[ids]=seam_distance/np.maximum(total,1.e-7)
    pattern = back_pattern(design[:,0],design[:,1])
    hand = 1-smooth(.08,.68,digit)
    cuff_fade = smooth(-4.10,-2.65,design[:,1])
    low = back*(pattern['low']*hand+finger_pad)*cuff_fade
    # Low shoulder at each digit, vanishing before each articulation joint.
    fine = back*pattern['fine']*hand*cuff_fade
    fine += back*digit*(-.014*gauss(digit_t,.08,.055)-.010*gauss(digit_t,.84,.050))
    fields = dict(design=design, back=back, hand=hand, digit=digit,
                  digit_t=digit_t, cuff_fade=cuff_fade, low=low, fine=fine)
    fields.update(finger_arc=finger_arc,finger_seam=finger_seam)
    return fields


def vertex_normals(data):
    values = np.zeros((len(data['positions']),3))
    faces = np.asarray(data['triangles'])
    ns = np.asarray(data['normals'])
    for k in range(3):
        np.add.at(values,faces[:,k],ns[:,k])
    return unit(values)


def to_canonical(data, master):
    """Invert each native skin blend, retaining its exact existing envelope."""
    p = np.asarray(data['positions'])
    n = vertex_normals(data)
    inverse = {k:np.linalg.inv(matrix(v)) for k,v in master['bones'].items()}
    delta = {k:matrix(v)@inverse[k] for k,v in data['bones'].items() if k in inverse}
    cp, cn, transforms = np.empty_like(p),np.empty_like(n),[]
    for i,w in enumerate(data['weights']):
        mat = sum(delta[k]*v for k,v in w.items())
        inv = np.linalg.inv(mat)
        cp[i] = (inv@np.r_[p[i],1])[:3]
        cn[i] = unit(mat[:3,:3].T@n[i])
        transforms.append(mat[:3,:3])
    return cp,cn,np.asarray(transforms)


def transported_normals(data,positions):
    faces=np.asarray(data['triangles']);old=np.asarray(data['positions'])
    _,inverse=np.unique(np.round(old,5),axis=0,return_inverse=True)
    def geo(p):
        corners=p[faces]
        cross=np.cross(corners[:,1]-corners[:,0],corners[:,2]-corners[:,0])
        out=np.zeros_like(p)
        for k in range(3):np.add.at(out,faces[:,k],cross)
        summed=np.zeros((inverse.max()+1,3));np.add.at(summed,inverse,out)
        return unit(summed[inverse])
    a,b=geo(old),geo(positions)
    axis=np.cross(a,b)[faces];dot=(a*b).sum(1)[faces,None]
    ns=np.asarray(data['normals'])
    return unit(ns+np.cross(axis,ns)+np.cross(axis,np.cross(axis,ns))/np.maximum(1+dot,1.e-8))
