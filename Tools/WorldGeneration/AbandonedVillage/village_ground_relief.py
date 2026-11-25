"""Village-local relief, mineral exposure and fixed PCG gravel pockets, in metres."""
from pathlib import Path
import json
import math

import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

from layout_geometry import house_paths, plot_geometry, wall_segments
from shop_frontages import flag_walks, public_frame
from village_tread import ramp, soil_variation, tread, window

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'SourceAssets/TemperateHillsVillage'


def frame(x, y, center, yaw):
    a = math.radians(yaw)
    dx, dy = x-center[0], y-center[1]
    return dx*math.cos(a)+dy*math.sin(a), dy*math.cos(a)-dx*math.sin(a)


def box(x, y, center, half, yaw=0.):
    u, v = frame(x, y, center, yaw)
    u, v = abs(u)-half[0], abs(v)-half[1]
    return np.hypot(np.maximum(u, 0.), np.maximum(v, 0.)) + np.minimum(np.maximum(u, v), 0.)


def distance(x, y, points):
    result = np.full((y.shape[0], x.shape[1]), 1000., dtype='f')
    for a, b in zip(points, points[1:]):
        dx, dy = b[0]-a[0], b[1]-a[1]
        length2 = dx*dx + dy*dy
        if length2 > .00001:
            t = np.clip(((x-a[0])*dx + (y-a[1])*dy)/length2, 0., 1.)
            np.minimum(result, np.hypot(x-a[0]-t*dx, y-a[1]-t*dy), out=result)
    return result


def mill_yard_gap(x,y,shape):
    nx,ny = shape['normal']
    center = shape['entry'][0]-3.765*nx, shape['entry'][1]-3.765*ny
    u,v = frame(x,y,center,math.degrees(math.atan2(ny,nx))-90.)
    return np.minimum(box(u,v,(.2,4.3),(11.2,12.3)),box(u,v,(13.5,7.8),(5.2,5.5)))


def fields(plan, kit):
    ex, ey = plan['surface_extent_m']
    x = np.arange(-ex, ex+.125, .25, dtype='f')[None, :]
    y = np.arange(-ey, ey+.125, .25, dtype='f')[:, None]
    perimeter = np.minimum(np.minimum(ex-abs(x), ey-abs(y)), (ex+ey-6.-abs(x)-abs(y)) / math.sqrt(2.))
    clearance = perimeter - 1.35
    wall_gap = clearance.copy()

    def reserve(signed_distance):
        np.minimum(clearance, signed_distance, out=clearance)

    def wall(line, half_width):
        gap = distance(x, y, line) - half_width
        np.minimum(wall_gap, gap, out=wall_gap)
        reserve(gap)

    for piece, width in wall_segments(plan):
        wall([piece[1:3], piece[3:5]], width)
    # Retain the original mineral/gravel distribution outside the smith's local patch.
    for a,b,width in plan.get('blacksmith',{}).get('smelting_yard',{}).get('prior_ground_segments',[]):
        wall([a,b],width)
    for a,b,width in plan.get('inn_old_wall_lines',[]):
        wall([a,b],width)
    for house in plan['houses']:
        shape = plot_geometry(house, kit[house[2]], plan)
        reserve(box(x, y, shape['center'], shape['half'], shape['angle']))
        reserve(distance(x, y, [shape['entry'], shape['step']]) - .85)
        if house[0] == '05':
            # Both the repaired apron surface and the permanent eastern grove
            # already have embedded props seated on the original mill datum.
            reserve(mill_yard_gap(x,y,shape))
    for yard in plan.get('service_clearings', []):
        reserve(box(x, y, yard['center'], yard['half'], yard['yaw']))
    # Retain the original exclusion only in the village-wide seeded pass. The
    # inn's local authoring pass owns the soil and gravel inside this patch.
    old = plan['tavern_forecourt']['baseline_scatter_reserve']
    for center, half, angle in old['boxes']:
        reserve(box(x, y, center, half, angle))
    reserve(distance(x, y, old['path'])-old['half_width'])
    sx, sy = old['point']
    reserve(np.hypot(x-sx, y-sy)-.4)
    # Existing stable wing, expanded west paddock, level turn court and individually modelled ruts.
    reserve(box(x, y, (33.7, 39.6), (24.8, 7.2)))
    reserve(box(x, y, (51.5, 24.), (6.5, 8.)))
    reserve(distance(x, y, [(59,5),(56.9,5.3),(55,6.3),(53.7,8.1),(52.7,10.7),(52.5,13.1),(52.5,16)])-2.)
    reserve(distance(x, y, [(51.4,5.05),(49.3,6.3),(47.7,8.2),(46.5,10.8),(46.25,13.5),(46.25,16)])-1.1)

    cx, cy = plan['chapel']['center']
    front, back, side, gate = plan['chapel']['yard']
    wall([(cx+u, cy+v) for u, v in [(front,gate),(front,side),(back,side),(back,-side),(front,-side),(front,-gate)]], .52)
    reserve(box(x, y, (cx, cy), (10.55, 6.4)))
    reserve(box(x, y, (cx-11., cy), (1.3, 1.4)))
    reserve(box(x, y, (cx-16.3, cy-2.85), (4.7, 6.65)))
    reserve(box(x, y, (cx-11.2, cy-3.45), (1.5, 2.)))
    reserve(np.hypot(x-(cx+front-9.), y-cy)-2.8)
    for gx, gy in [(-5.7,9.07),(-3.77,9.50),(-1.99,8.86)]:
        reserve(np.hypot(x-(cx+1.25*gx), y-(cy+1.25*gy)) - 1.85)
    for gx, gy in plan['rubble']:
        reserve(np.hypot(x-gx, y-gy) - 1.25)

    road_edge = np.full_like(clearance, 1000.)
    cart_axis = road_edge.copy()
    for points, width in [(r['points'],r['width']) for r in plan['roads']] + house_paths(plan, kit):
        d = distance(x, y, points)
        np.minimum(road_edge, d-width*.5, out=road_edge)
        if width >= 4.:
            np.minimum(cart_axis, d, out=cart_axis)
    sqx, sqy, rx, ry = plan['square']
    square = (np.hypot((x-sqx)/rx, (y-sqy)/ry)-1.) * min(rx, ry)
    traffic = 1.-ramp((np.minimum(road_edge, square)+.45)/1.55)
    # Work in one continuous village frame. Large drift areas have stretched
    # grains, finer deposits cross them at another angle. The warp never
    # restarts at a road segment, building reservation or streaming boundary.
    drift = soil_variation(x, y, 13.7, 23033)
    cross = soil_variation(x, y, 8.3, 23039)
    u = .83*x+.56*y + 2.8*cross
    v = -.56*x+.83*y + 3.4*drift
    broad = soil_variation(u*.65, v, 3.9, 23011)
    mid = soil_variation(.45*u-.89*v, .89*u+.45*v, 1.58, 23017)
    grain = soil_variation(v+.26*u, u*.72-.38*v, .49, 23023)
    shoulder = np.exp(-((road_edge-(.85+.52*cross))/(1.35+.65*drift))**2)
    foot = np.exp(-((wall_gap-(2.45+.63*broad))/(1.58+.59*cross))**2)
    shelter = foot*(.45+.55*ramp(.50+.69*drift+.42*mid))
    safe = ramp((clearance-.85)/(1.75+.55*cross))
    lens = ramp((.48*broad+.31*mid+.33*drift+.16)/.72)
    rut = np.exp(-((cart_axis-.79-.11*cross-.09*mid)/(.40+.08*broad))**2)
    rut *= .41+.59*ramp(.57+.85*drift+.39*mid)
    # Old planted tufts and loose masonry sit at the original datum. Retain
    # that as a lower bound off the road; cut into the ground only in wheelways.
    gate_gap = np.minimum(box(x,y,(-ex,0.),(5.5,5.8)), box(x,y,(ex,5.),(5.5,4.8)))
    swing = ramp((gate_gap-.55)/1.6)
    rise = np.maximum(0.,(1.-.72*traffic)*(2.7+5.8*broad+2.9*mid+2.7*drift)
                      + (4.8*shelter+5.5*shoulder)*(.32+.68*lens))
    height = safe*swing*(rise-4.7*rut)
    soil = safe*ramp((.24+.25*lens+.23*shoulder+.24*shelter+.14*mid+.14*grain-.10*drift)/.86)
    mineral = safe*ramp((.55*lens+.37*shoulder+.29*shelter+.20*mid+.17*grain-.31)/.58)*(1.-.84*traffic)
    # At 0.5 in the packed B channel the shader crosses into pale road stone.
    # Isolated meadow deposits only dust the earth. Exposed shoulders and
    # masonry can build up enough mineral to cross that threshold locally.
    mineral *= .70+.16*shoulder+.075*shelter+.035*grain
    # Small washed-out runs break up the bare commons. Use short portions
    # of bent contours and taper their ends so they don't become parallel stripes.
    deposit = soil_variation(.31*u+.95*v, .95*u-.31*v, 2.37, 23041)
    thread = np.exp(-((.70*broad+.30*cross+.24*mid+.11*grain)/(.19+.045*deposit))**2)
    ends = ramp((.57*deposit+.24*drift+.20*mid+.16)/.66)
    silt = thread*ends*(1.-.78*traffic)
    mineral = np.maximum(mineral, safe*silt*(.74+.15*grain+.06*mid))
    soil = np.maximum(soil, safe*silt*(.59+.17*grain))
    density = safe*swing*ramp((.22+.49*lens+.33*shoulder+.35*shelter+.15*mid+.11*drift)/1.02)*(1.-.96*traffic)
    # Follow wear and masonry close to either edge. In open ground let
    # the direction of the elongated deposits guide individual stone drifts.
    edge = np.minimum(road_edge, wall_gap)
    gy, gx = np.gradient(np.where(edge<4., edge, 4.), .25)
    return height, soil, mineral, density, (gx, gy, shelter, shoulder, drift)


def mask_floor(packed, soil, mineral):
    # Input samples lie on quarter-metre lattice vertices. Match the texture's
    # texel centres without rescaling the metre coordinates at the boundary.
    def upsample(field):
        h, w = field.shape
        return np.asarray(Image.fromarray(field.astype('float32')).resize(
            packed.size, Image.Resampling.BILINEAR, box=(.5,.5,w-.5,h-.5)))

    data = np.array(packed.convert('RGBA'))
    for channel, image in [(1, soil*.80), (2, mineral*.565)]:
        data[:,:,channel] = np.maximum(data[:,:,channel], np.rint(upsample(image)*255).astype('uint8'))
    return Image.fromarray(data)


def dress_shop_flags(packed,plan,kit):
    # Old approaches remain visible where a shop is still in ruins. The new
    # public approach follows the actual flags; the mesh and its repair state
    # remain the responsibility of the shop. Only exposed earth is painted.
    houses={h[0]:h for h in plan['houses']}
    mill=plot_geometry(houses['05'],kit[houses['05'][2]],plan)
    ex,ey=plan['surface_extent_m']
    w,h=packed.size
    px=((np.arange(w)[None,:]+.5)/w-.5)*(2*ex)
    py=((np.arange(h)[:,None]+.5)/h-.5)*(2*ey)
    for lot in ('06','09'):
        house=houses[lot]
        shape=plot_geometry(house,kit[house[2]],plan)
        origin,yaw=public_frame(house,shape)
        walks=flag_walks(house,shape,plan)
        xs,ys=zip(*(p for line in walks for p in line))
        (rows,cols),x,y=window(px,py,(min(xs)-2.,min(ys)-2.,max(xs)+2.,max(ys)+2.))
        u,v=frame(x,y,origin,yaw)
        noise=soil_variation(x,y,.85,7021+int(lot))
        grit=soil_variation(x,y,.24,7031+int(lot))
        # Local +Y is indoors. Past the bakery corner the path turns along
        # the side wall; allow its outside shoulder to meet the main street.
        half=3.92 if lot=='06' else 4.86
        outside=ramp((np.maximum(-v,abs(u)-half)+.10)/.32)
        outside*=ramp(mill_yard_gap(x,y,mill)/.35)
        soil=np.zeros_like(outside)
        mineral=np.zeros_like(outside)
        for index,line in enumerate(walks):
            width=.60 if lot=='06' and index==0 else .44
            points=[(*p,width+(.15 if i==0 else 0.)) for i,p in enumerate(line)]
            band=tread(x,y,points,.055*noise+.032*grit)
            walked=ramp((band+.40+.13*noise+.065*grit)/.78)
            strength=.82 if lot=='06' and index==0 else .70
            soil=np.maximum(soil,walked*np.clip(strength+.12*noise+.11*grit,.42,.94))
            mineral=np.maximum(mineral,walked*np.clip(.37+.11*noise+.08*grit,.18,.48))
        area=(cols.start,rows.start,cols.stop,rows.stop)
        data=np.array(packed.crop(area))
        for channel,layer in ((1,soil),(2,mineral)):
            data[:,:,channel]=np.maximum(data[:,:,channel],np.rint(255*layer*outside).astype('uint8'))
        packed.paste(Image.fromarray(data),area)
    return packed


def gravel_points(density, guides, plan):
    ex, ey = plan['surface_extent_m']
    rng = np.random.default_rng(plan['ground_dressing']['seed'])
    pockets, occupied = [], {}
    def sample(field, px, py):
        return map_coordinates(field, np.array([np.atleast_1d(py+ey),np.atleast_1d(px+ex)])*4.,
                               order=1, mode='constant')
    # Uniform proposals have no cell centres. The deposit map supplies broad
    # empty spaces; sort only after the footprint and global budget decisions.
    proposals = math.ceil(4*ex*ey*.23)
    px, py = rng.uniform(-ex,ex,proposals), rng.uniform(-ey,ey,proposals)
    keep = rng.random(proposals)<sample(density,px,py)
    px, py = px[keep], py[keep]
    guide = np.stack([sample(g,px,py) for g in guides],axis=1)
    for x,y,(gx,gy,wall,road,drift) in zip(px,py,guide):
        near_edge = math.hypot(gx,gy)>.35
        angle = math.atan2(gx,-gy) if near_edge else .58+.98*drift
        angle += rng.normal(0.,.27 if near_edge else .70)
        if rng.random()<.5:
            angle += math.pi
        style = rng.random()
        if style < .29:
            count, length, width = 1, 0., 0.
        elif style < .59+.15*wall:
            count, length, width = rng.integers(2,7), rng.uniform(.24,.95), rng.uniform(.16,.46)
        else:
            count, length, width = rng.integers(4,11), rng.uniform(1.1,2.8), rng.uniform(.14,.43)
        along = rng.uniform(-1.,1.,count)
        side = rng.normal(0.,width,count)+rng.uniform(-.42,.42)*along**2*length
        sx = x+length*along*math.cos(angle)-side*math.sin(angle)
        sy = y+length*along*math.sin(angle)+side*math.cos(angle)
        allowed = sample(density,sx,sy)
        primary = 0 if wall>.22 else (1 if road>.3 else int(rng.integers(3)))
        for j in range(count):
            if allowed[j]<.08:
                continue
            size = round(rng.uniform(9,23) if rng.random()<.18+.28*wall else rng.uniform(4,13))
            cx, cy = round(100*sx[j]), round(100*sy[j])
            # The diagonal of a diameter-wide mesh box is a conservative
            # footprint. Check the final rounded coordinates across all groups.
            radius = .71*size+1
            key = cx//50, cy//50
            if any((cx-ox)**2+(cy-oy)**2 < (radius+r)**2
                   for dx in (-1,0,1) for dy in (-1,0,1)
                   for ox,oy,r in occupied.get((key[0]+dx,key[1]+dy),())):
                continue
            occupied.setdefault(key,[]).append((cx,cy,radius))
            variant = primary if rng.random()<.61 else int(rng.integers(3))
            turn = angle+rng.normal(0.,.57) if count>=4 and rng.random()<.58 else rng.uniform(0.,2.*math.pi)
            pockets.append((cx,cy,size,round(turn*128/math.pi)%256,variant))
            if len(pockets)>=1157:
                return sorted(pockets,key=lambda p:(p[1],p[0]))
    pockets.sort(key=lambda p:(p[1],p[0]))
    return pockets


def write_native(height, pockets, plan, sample_stride=4):
    ex, ey = plan['surface_extent_m']
    grid = np.rint(height[::sample_stride,::sample_stride]).astype('int8')
    lines = ['// Generated by village_ground_relief.py. Local XY and elevations are centimetres.',
             f'constexpr int32 HalfX={ex*100}, HalfY={ey*100}, Columns={grid.shape[1]}, Rows={grid.shape[0]};',
             'constexpr int8 Relief[Rows][Columns]={']
    lines += ['    {'+','.join(map(str,row))+'},' for row in grid]
    lines += ['};', 'constexpr FGravel Gravel[]={']
    lines += ['    '+','.join('{'+','.join(map(str,p))+'}' for p in pockets[i:i+8])+',' for i in range(0,len(pockets),8)]
    lines += ['};','']
    output = ROOT/'Source/FPSGAME/WorldGeneration/TemperateVillageGroundData.inl'
    output.write_text('\n'.join(lines),encoding='utf-8')
    print(f'{grid.shape[1]} x {grid.shape[0]} elevations; {grid.min()} to {grid.max()} cm; {len(pockets)} gravel instances')


def apply_ground(packed, plan, kit):
    # Keep the seed sequence and the gravel budget of the published village.
    # A local courtyard refit must not reshuffle rocks in unrelated streets.
    baseline=plan
    inn=plan.get('tavern',{}).get('inn')
    if inn:
        baseline={**plan,'tavern':{k:v for k,v in plan['tavern'].items() if k!='inn'}}
    if inn and inn.get('hall_road'):
        baseline['inn_old_wall_lines']=[w['line'] for w in inn['hall_road']['retired_walls']]
    height, soil, mineral, density, guides = fields(baseline, kit)
    stones=gravel_points(density,guides,baseline)
    packed=dress_shop_flags(mask_floor(packed,soil,mineral),baseline,kit)
    if inn:
        from inn_frontage import patch
        house=next(h for h in plan['houses'] if h[0]==plan['tavern']['house'])
        packed,height,stones=patch(packed,height,stones,plan,plot_geometry(house,kit[house[2]],plan))
    from smith_apron import patch as fit_smith_apron
    packed,height,stones=fit_smith_apron(packed,height,stones,plan)
    write_native(height,stones,plan)
    from inn_forecourt_wear import paint
    return paint(packed, plan)


if __name__ == '__main__':
    def read(name):
        return json.loads((SOURCE/name).read_text(encoding='utf-8'))
    path = SOURCE/'RoadMask.png'
    # Keep the hand-placed streets, mill yard and verge separate from this
    # replaceable procedural layer; earlier passes must not accumulate.
    with Image.open(SOURCE/'RoadMaskBase.png') as im:
        result = apply_ground(im, read('layout.json'), read('house-pieces.json'))
    result.save(path)
