"""Bake a centimetre adjustment to the sited village's existing one-metre ground grid."""
import argparse
import json
import math
import re
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, map_coordinates

from generate_village_relief import FOLLOW, ROOT
from layout_geometry import house_paths, plot_geometry, wall_segments
from village_ground_relief import box, distance, mill_yard_gap
from village_tread import ramp


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def refitted_sites(x, y, plan):
    # The expanded stable and the relocated store are level, authored on the
    # village datum. The older serialized hill offset also predates these pads.
    gunshop=next(h for h in plan['houses'] if h[0]=='09')
    return np.minimum(box(x,y,(gunshop[3],gunshop[4]-.3),(6.2,6.2),gunshop[5]),
                      box(x,y,(33.65,39.5),(24.85,7.30)))


def ground_clearance(x, y, plan, kit, contacts):
    """Distances in metres to fixed geometry, in village-local coordinates."""
    clear = np.full_like(x, 1000., dtype=float)

    def reserve(gap):
        np.minimum(clear, gap, out=clear)

    def rect(center, half, yaw=0.):
        reserve(box(x, y, center, half, yaw))

    def trail(points, half):
        reserve(distance(x, y, points)-half)

    for house in plan['houses']:
        shape = plot_geometry(house, kit[house[2]], plan)
        rect(shape['center'], shape['half'], shape['angle'])
        trail([shape['entry'], shape['step']], .95)
        if house[0] == '05':
            reserve(mill_yard_gap(x, y, shape))
    for yard in plan['service_clearings']:
        rect(yard['center'], yard['half'], yard['yaw'])
    for piece, half in wall_segments(plan):
        trail([piece[1:3], piece[3:5]], half)
    x0,y0,x1,y1 = plan['blacksmith']['smelting_yard']['bounds_m']
    rect(((x1+x0)/2, (y1+y0)/2), ((x1-x0)/2, (y1-y0)/2))

    # The streamed sublevel does not own the chapel, workshop, tower or gate collision.
    chapel = plan['chapel']
    cx,cy = chapel['center']
    front,back,side,gate = chapel['yard']
    fence = [(front,gate),(front,side),(back,side),(back,-side),(front,-side),(front,-gate)]
    trail([(cx+u,cy+v) for u,v in fence], .52)
    rect((cx,cy),(10.55,6.4))
    rect((cx-11.,cy),(1.3,1.4))
    rect((cx-16.3,cy-2.85),(4.7,6.65))
    reserve(np.hypot(x-(cx+front-9), y-cy)-5.)
    for gx,gy in ((-5.70,9.07),(-3.77,9.50),(-1.99,8.86)):
        reserve(np.hypot(x-(cx+1.25*gx), y-(cy+1.25*gy))-1.85)
    rect((52.50,-5.45),(3.40,6.24))
    rect((52.50,1.65),(1.5,1.25))
    reserve(np.hypot(x-52.50,y-2.90)-.55)  # shared grading sample for the workshop
    rect((58.73,-6.05),(5.,5.))
    rect((43.,38.),(15.,6.))
    rect((51.5,24.),(6.5,8.))
    trail([(59,5),(56.9,5.3),(55,6.3),(53.7,8.1),(52.7,10.7),(52.5,13.1),(52.5,16)],2.)
    trail([(51.4,5.05),(49.3,6.3),(47.7,8.2),(46.5,10.8),(46.25,13.5),(46.25,16)],1.1)
    ex,ey = plan['surface_extent_m']
    rect((ex,5.),(3.3,4.8))
    rect((-ex,0.),(3.3,5.5))
    # Both intact and ruined structures are captured. The only omitted contacts
    # are instances the runtime already reseats from this same triangle grid.
    for left,bottom,right,top,name,instanced in contacts:
        if instanced and name.startswith(FOLLOW):
            continue
        near = (x>=left-6)&(x<=right+6)&(y>=bottom-6)&(y<=top+6)
        gap = np.hypot(np.maximum(np.maximum(left-x[near],x[near]-right),0.),
                       np.maximum(np.maximum(bottom-y[near],y[near]-top),0.))
        clear[near] = np.minimum(clear[near],gap)
    return clear


def road_shape(x, y, plan, kit):
    gap = np.full(x.shape, 1000.)
    crown = np.zeros_like(gap)
    gutter = np.zeros_like(gap)
    roads = [(r['points'],r['width']) for r in plan['roads']] + house_paths(plan,kit)
    lanes = [[(*p,width/2) for p in points] for points,width in roads]
    lanes += [plan['tavern']['inn']['hall_road']['stations'], plan['tavern_forecourt']['trail']]
    for stations in lanes:
        for a,b in zip(stations,stations[1:]):
            dx,dy = b[0]-a[0],b[1]-a[1]
            t = np.clip(((x-a[0])*dx+(y-a[1])*dy)/max(dx*dx+dy*dy, .0001),0.,1.)
            half = a[2] + t*(b[2]-a[2])
            d = np.hypot(x-a[0]-t*dx,y-a[1]-t*dy)
            gap = np.minimum(gap,d-half)
            crown = np.maximum(crown,(1.-ramp(d/half))*np.clip(half/2.,.45,1.))
            gutter = np.maximum(gutter,np.exp(-((d-half+.12)/.92)**2))
    cx,cy,rx,ry = plan['square']
    plaza = (np.hypot((x-cx)/rx,(y-cy)/ry)-1.)*min(rx,ry)
    return np.minimum(gap,plaza), crown, gutter*(1.-crown)


def limit_grade(delta, maximum):
    """Limit the added grade between knots without moving locked supports.

    Trim only the end(s) that introduced the excess, toward their starting
    height. Diagonal edges are included because the ground uses triangles.
    """
    for _ in range(32):
        scale = np.ones_like(delta)
        for dy,dx,step in ((0,1,1.),(1,0,1.),(1,1,math.sqrt(2)),(1,-1,math.sqrt(2))):
            rows,cols=delta.shape
            a=np.s_[0:rows-dy,max(0,-dx):cols-max(0,dx)]
            b=np.s_[dy:rows,max(0,dx):cols-max(0,-dx)]
            diff=delta[a]-delta[b]
            sign=np.sign(diff)
            allowed=step*np.minimum(maximum[a],maximum[b])
            excess=np.maximum(0.,np.abs(diff)-allowed)
            movable_a=sign*delta[a]>0
            movable_b=sign*delta[b]<0
            room=np.where(movable_a,np.abs(delta[a]),0.)+np.where(movable_b,np.abs(delta[b]),0.)
            factor=1.-excess/np.maximum(room,1.e-9)
            np.minimum(scale[a],np.where(movable_a,factor,1.),out=scale[a])
            np.minimum(scale[b],np.where(movable_b,factor,1.),out=scale[b])
        if np.min(scale)>.9999:
            break
        delta=delta*scale
    return delta


def bake(base, donor, contacts_path, out):
    layout_dir=ROOT/'SourceAssets/TemperateHillsVillage'
    plan=read(layout_dir/'layout.json')
    kit=read(layout_dir/'house-pieces.json')
    hill=read(base/'hill.json')
    old=np.fromfile(base/'settlement.i16','<i2').reshape(146,119).astype(float)
    row,col=np.indices(old.shape)
    vx,vy=hill['site_min_m']
    cx,cy=hill['village_center_m']
    x,y=cy-(vy+row),vx+col-cx
    ex,ey=plan['surface_extent_m']
    native=(ROOT/'Source/FPSGAME/WorldGeneration/TemperateVillageGroundData.inl').read_text(encoding='utf8')
    raw=native.split('Relief[Rows][Columns]={',1)[1].split('};',1)[0]
    original=np.array(re.findall(r'-?\d+',raw),dtype=float).reshape(2*ey+1,2*ex+1)
    total=old.copy()
    inside=(np.abs(x)<ex)&(np.abs(y)<ey)
    total[inside]+=original[y[inside]+ey,x[inside]+ex]

    clear=ground_clearance(x,y,plan,kit,read(contacts_path))
    # Even the farthest corner of a 1 m support triangle stays at its original Z.
    footing=ramp((clear-math.sqrt(2)) / 3.15)
    perimeter=np.minimum.reduce((ex-abs(x),ey-abs(y),(ex+ey-6-abs(x)-abs(y))/math.sqrt(2)))
    edge=ramp((perimeter-2.3)/4.)
    gap,crown,gutter=road_shape(x,y,plan,kit)
    road=1.-ramp((gap-.10)/2.8)

    # Non-repeating connected crests from the existing measured forest DEM.
    # Exclude macro hillslope, then separate the walk-scale and yard-scale forms.
    dem=np.fromfile(donor,'<f4',count=505*505).reshape(505,505)
    coords=[189+row*122./145,63+col*98./118]
    def band(narrow,wide):
        data=map_coordinates(gaussian_filter(dem,narrow)-gaussian_filter(dem,wide),
                             coords,order=1,prefilter=False)
        centered=data-np.median(data)
        return np.tanh(centered/max(1.,np.percentile(abs(centered),65)))
    long=band(3.,9.)
    short=band(1.25,3.5)
    old_form=np.tanh((total-gaussian_filter(total,4.5))/19.)
    # A continuous low-frequency component crosses all branches and junctions.
    # Centre the road profile on exposed tread: the measured donor contains
    # a single long concave slope that would otherwise sink most of Main Street.
    rng=np.random.default_rng(251142)
    noise=gaussian_filter(rng.standard_normal(old.shape),4.2)
    exposed=(gap<0)&(footing>.6)&(edge>.9)
    roll=.45*long+.55*np.tanh(noise/noise.std())
    roll-=np.median(roll[exposed])
    roll=np.tanh(roll/max(.15,np.percentile(abs(roll[exposed]),65)))
    lane=22.*roll+5.*short+4.*old_form+6.5*crown-(3.5+2.*short)*gutter
    yard=39.*long+16.*short+15.*old_form
    delta=(road*lane+(1.-road)*yard)*footing*edge
    delta=np.rint(limit_grade(delta,16.-6.*road)).astype('int8')
    site_gap=refitted_sites(x,y,plan)
    transition=ramp((site_gap-math.sqrt(2))/3.15)
    delta=np.rint(transition*delta-(1.-transition)*old)
    if np.max(abs(delta))>127:raise ValueError('Village adjustment exceeds int8 range')
    delta=delta.astype('int8')
    out.mkdir(parents=True,exist_ok=True)
    Image.fromarray((32768+delta.astype('int32')).astype('uint16')).save(out/'H_StreetYardDeltaCm.png')
    Image.fromarray((32768+total+delta).astype('uint16')).save(out/'H_StreetYardGroundCm.png')
    output=ROOT/'Source/FPSGAME/WorldGeneration/ForestVillageStreetRelief.inl'
    lines=['// Generated by prepare_village_street_relief.py. Signed centimetres on the sited village grid.',
           'constexpr int8 StreetAndYardCm[Rows][Columns] = {']
    lines += ['    {'+','.join(map(str,r))+'},' for r in delta]
    content='\n'.join(lines+['};',''])
    if not output.is_file() or output.read_text(encoding='utf8')!=content:
        output.write_text(content,encoding='utf8')
    def interval(mask):
        return np.percentile(delta[mask],[10,90]).round(1).tolist()
    playable=(footing>.65)&(edge>.95)
    result=dict(grid_xy=[old.shape[1],old.shape[0]],pitch_m=1,changed_knots=int(np.count_nonzero(delta)),
                adjustment_cm=[int(delta.min()),int(delta.max())],road_p10_p90_cm=interval(playable&(gap<0)),
                yard_p10_p90_cm=interval(playable&(gap>2.8)),foundation_lock_m=round(math.sqrt(2),3),
                foundation_blend_m=3.15,source=base.name)
    (out/'generation.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for arg in ('base','donor','contacts','out'):
        parser.add_argument(arg,type=Path)
    args=parser.parse_args()
    bake(args.base,args.donor,args.contacts,args.out)
