"""Draw the dimensioned village plan and its co-registered road coverage texture."""
from pathlib import Path
import json
import math
import random
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy.ndimage import gaussian_filter, minimum_filter
from layout_geometry import approach_path, nearest, plot_geometry, wall_segments
from village_tread import street_wear, chapel_wear, protected_turf, ramp
from windmill_footing import dress_ground
from village_ground_relief import apply_ground

out = Path(__file__).resolve().parents[3] / 'SourceAssets/TemperateHillsVillage'
plan_only = '--plan-only' in sys.argv
mask_only = '--road-mask-only' in sys.argv
plan = json.loads((out/'layout.json').read_text(encoding='utf-8'))
dressing = plan['ground_dressing']
kit = json.loads((out/'house-pieces.json').read_text(encoding='utf-8'))
ex,ey = plan.get('surface_extent_m',plan['extent_m'])
streets = [(r['points'], r['width']) for r in plan['roads']]
roads = list(streets)
chapel=plan['chapel']
hx,hy=chapel['center']
front,back,side,opening=chapel['yard']
def rotate(x,y,degrees):
    angle=math.radians(degrees)
    return x*math.cos(angle)-y*math.sin(angle), x*math.sin(angle)+y*math.cos(angle)

houses=[]
house_shapes={}
for house in plan['houses']:
    num,name,model,x,y,angle=house
    parts=kit[model]
    geometry=plot_geometry(house,parts,plan)
    house_shapes[num]=geometry
    entry,step=geometry['entry'],geometry['step']
    roads.append(approach_path(house,geometry,plan,streets))
    houses.append((num,name,model,x,y,angle,entry))

# Native placement and the design sheet share one metric drawing.
header=['// Generated from SourceAssets/TemperateHillsVillage/layout.json by draw_plan.py.',
        '#pragma once','namespace TemperateVillageLayout','{',
        f'inline constexpr double HalfX={plan["extent_m"][0]*100}., HalfY={plan["extent_m"][1]*100}.;',
        f'inline constexpr double ChapelX={hx*100:.1f}, ChapelY={hy*100:.1f}, ChapelTrailX={chapel["trail"][0]*100:.1f}, ChapelTrailY={chapel["trail"][1]*100:.1f};',
        f'inline constexpr double CourtFront={front*100:.1f}, CourtBack={back*100:.1f}, CourtSide={side*100:.1f}, CourtOpening={opening*100:.1f};',
        'struct FRoad { double X,Y,DX,DY,HalfWidth; };','inline constexpr FRoad Roads[] = {']
def row(*values):return '    {'+', '.join(f'{v:.3f}' for v in values)+'},'
inn_stations=plan.get('tavern',{}).get('inn',{}).get('hall_road',{}).get('stations',[])
inn_links=[([a[:2],b[:2]],a[2]+b[2]) for a,b in zip(inn_stations,inn_stations[1:])]
for pts,width in roads+inn_links:
    for a,b in zip(pts,pts[1:]):
        if math.dist(a,b)>.01:
            header.append(row(a[0]*100,a[1]*100,(b[0]-a[0])*100,(b[1]-a[1])*100,width*50))
header.extend(['};','struct FBox { double X,Y,HalfX,HalfY,Cos,Sin; };','inline constexpr FBox Beds[] = {'])
for num,_,model,x0,y0,a,_ in houses:
    shape=house_shapes[num]
    header.append(row(shape['center'][0]*100,shape['center'][1]*100,shape['half'][0]*100,shape['half'][1]*100,
                      math.cos(math.radians(a)),math.sin(math.radians(a))))
for x0,y0,rx,ry in plan['meadows']+[plan['square']]:
    header.append(row(x0*100,y0*100,rx*100,ry*100,1,0))
for service in plan.get('service_clearings',[]):
    a=math.radians(service['yaw'])
    header.append(row(*[v*100 for v in service['center']],*[v*100 for v in service['half']],math.cos(a),math.sin(a)))
if yard := plan.get('blacksmith',{}).get('smelting_yard'):
    x0,y0,x1,y1=yard['bounds_m']
    header.append(row((x0+x1)*50,(y0+y1)*50,(x1-x0)*50,(y1-y0)*50,1,0))
# Reserve the authored wall skirts and road shoulders for the small ground-cover
# palette. The same seed-local strips travel with the settlement.
for (_,x1,y1,x2,y2,_),half_width in wall_segments(plan):
    dx,dy=x2-x1,y2-y1
    length=math.hypot(dx,dy)
    header.append(row((x1+x2)*50,(y1+y2)*50,length*50,
                      (half_width+dressing['wall_skirt_m'])*100,dx/length,dy/length))
main=plan['roads'][0]
for a,b in zip(main['points'],main['points'][1:]):
    dx,dy=b[0]-a[0],b[1]-a[1]
    length=math.hypot(dx,dy)
    header.append(row((a[0]+b[0])*50,(a[1]+b[1])*50,length*50,
                      (main['width']*.5+dressing['road_verge_m'])*100,dx/length,dy/length))
header.extend(['};','}'])
native=Path(__file__).resolve().parents[3]/'Source/FPSGAME/WorldGeneration/TemperateVillageLayout.inl'
if not plan_only and not mask_only:
    native.write_text('\n'.join(header)+'\n', encoding='utf-8')

if '--header-only' in sys.argv:
    raise SystemExit(0)

# U and V of the terrain's village material increase along local X and Y.
px=20
rows,cols=int(2*ey*px),int(2*ex*px)
y,x=np.ogrid[0:rows,0:cols]
x=(x+.5)/px-ex; y=(y+.5)/px-ey
def offset(line):
    distance=np.full((rows,cols),1e3)
    for a,b in zip(line,line[1:]):
        dx,dy=b[0]-a[0],b[1]-a[1]
        if dx*dx+dy*dy<1e-8:
            continue
        t=np.clip(((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy),0,1)
        distance=np.minimum(distance,np.hypot(x-a[0]-t*dx,y-a[1]-t*dy))
    return distance
rand=np.random.default_rng(523)
grain=rand.normal(size=(rows,cols)).astype('f')
coarse=gaussian_filter(grain,9)*30
noise=.17*coarse+.11*gaussian_filter(grain,2)*6
cartways=[(line,width) for line,width in streets if width>=main['width']]
cart_distance=np.full_like(grain,1e3)
foot_soil=np.zeros_like(grain)
coverage=np.zeros_like(grain)
rock_edge=np.full_like(grain,1e3)
clearance=np.full_like(grain,1e3)
# Plant reservations remain tied to the authored walking and turning widths.
plant_coverage=np.zeros_like(grain)
for i,(line,width) in enumerate(roads):
    d=offset(line)
    clearance=np.minimum(clearance,d-width*.5-dressing['road_buffer_m'])
    alpha=np.clip((width*.5-d+noise+.24)/.73,0,1)
    if i==0:
        tracks=np.exp(-((d-.91)/.36)**2)
        alpha*=.67+.29*tracks+.035*np.clip(coarse,-1,1)
    plant_coverage=np.maximum(plant_coverage,alpha)
    if i<len(streets) and width>=main['width']:
        cart_distance=np.minimum(cart_distance,d)
        continue
    # Narrow lanes wear down to packed soil along a foot line. Only the
    # busiest strip exposes the coarse stone in the road texture.
    path_half=width*.5
    busy=width>=3.
    foot_width=path_half*(.68 if busy else .58)
    edge=d-foot_width
    tread=np.clip((.36-edge+noise*.55)/.72,0,1)
    grit=np.clip(.45+.22*coarse,.10,.83)
    foot_soil=np.maximum(foot_soil,tread*(.76+.18*grit))
    surface_distance=np.maximum(edge+.22,.16+.37*(1-grit)-(.24 if busy else 0.))
    rock_edge=np.minimum(rock_edge,surface_distance)
    coverage=np.maximum(coverage,tread*(.67+.19*grit))

# The main street and its two gate approaches are one cart route. Merge their
# centre lines before deriving the wheel bands, including at segment joins.
gauge=.86+.06*np.sin(x*.14+y*.19)
tracks=np.exp(-((cart_distance-gauge)/(.28+.035*np.cos(x*.19-y*.23)))**2)
cart_angle=np.sin(.24*x+.13*y)
cart=np.clip((main['width']*.5-cart_distance+noise+.24)/.73,0,1)
cart*=np.clip(.67+.31*tracks+.025*cart_angle+.025*coarse,0,1)
# Foot traffic and carts overlap at junctions. Here the grass between the
# wheels is worn away in a short fan before the paired tracks resume.
junction_wear=np.zeros_like(grain)
for line,width in streets:
    if width>=main['width']:
        continue
    for end in (line[0],line[-1]):
        if math.dist(end,nearest(end,cartways))<.25:
            along=((x-end[0])/2.5)**2+((y-end[1])/1.7)**2
            crossing=np.exp(-along)
            junction_wear=np.maximum(junction_wear,crossing)
            cart=np.maximum(cart,crossing*.90*np.clip(1.5-cart_distance*.5,0,1))
# R modulates an existing road surface but the material floors that weight at
# .67. Also open the signed stone extent (B) between the wheels so that turf
# actually shows through there, without cutting either rut or any busy fork.
lengthwise=np.clip(.82+.25*np.sin(.36*x+.11*y)+.13*np.cos(.67*x-.18*y)+.07*coarse,.20,1.)
median=np.clip((.66-cart_distance+.05*noise)/.44,0,1)*lengthwise*(1.-junction_wear)
cart_edge=np.maximum(cart_distance-main['width']*.5,2.55*median-1.45)
street_patch,street_blend,bank_stone,bank_strength,bank_earth=street_wear(
    x,y,main,roads,cart_distance,noise)
cart_edge[street_patch]+=(bank_stone-cart_edge[street_patch])*street_blend
cart[street_patch]+=(bank_strength-cart[street_patch])*street_blend
coverage=np.maximum(coverage,cart)
rock_edge=np.minimum(rock_edge,cart_edge)
cx,cy,rx,ry=plan['square']
square=1-np.hypot((x-cx)/rx,(y-cy)/ry)
rock_edge=np.minimum(rock_edge,-square*min(rx,ry))
coverage=np.maximum(coverage,np.clip(square*4+noise,0,1)*.85)
plant_coverage=np.maximum(plant_coverage,np.clip(square*4+noise,0,1)*.85)
coverage_image=Image.fromarray((coverage*255).astype('uint8'))

# Signed clearance includes the full road widths, door approaches, chapel court
# and house footprints. The author uses it with each mesh's complete footprint.
def box_distance(cx,cy,half_x,half_y,angle=0):
    a=math.radians(angle)
    dx=(x-cx)*math.cos(a)+(y-cy)*math.sin(a)
    dy=(y-cy)*math.cos(a)-(x-cx)*math.sin(a)
    qx,qy=np.abs(dx)-half_x,np.abs(dy)-half_y
    return np.hypot(np.maximum(qx,0),np.maximum(qy,0))+np.minimum(np.maximum(qx,qy),0)
for num,_,model,cx,cy,angle,_ in houses:
    shape=house_shapes[num]
    clearance=np.minimum(clearance,box_distance(*shape['center'],shape['half'][0]+.15,shape['half'][1]+.15,angle))
for service in plan.get('service_clearings',[]):
    clearance=np.minimum(clearance,box_distance(*service['center'],*service['half'],service['yaw']))
clearance=np.minimum(clearance,box_distance(hx+(front+back)*.5,hy,(back-front)*.5+.4,side+.4))
cx,cy,rx,ry=plan['square']
clearance=np.minimum(clearance,(np.hypot((x-cx)/rx,(y-cy)/ry)-1)*min(rx,ry)-.15)
clearance=np.minimum(clearance,np.minimum(ex-np.abs(x),ey-np.abs(y))-.15)

# Eroded soil feathers out below stone and into the grassy shoulder.
shoulder=cart_distance-main['width']*.5
patch=np.clip(.55+.32*coarse+.11*gaussian_filter(grain,3)*8,.12,1)
soil=np.clip((dressing['road_verge_m']-shoulder+noise*.7)/1.15,0,1)*patch*.72
soil*=np.clip((shoulder+.4)/.45,0,1)
soil[street_patch]*=1.-street_blend
for (_,x1,y1,x2,y2,_),half_width in wall_segments(plan):
    dx,dy=x2-x1,y2-y1
    length=math.hypot(dx,dy)
    along=((x-x1)*dx+(y-y1)*dy)/length
    across=np.abs((y-y1)*dx-(x-x1)*dy)/length
    ends=np.clip(np.minimum(along,length-along)/.3,0,1)
    edge=np.clip((half_width+dressing['wall_skirt_m']-across+noise*.55)/.8,0,1)
    soil=np.maximum(soil,edge*ends*(.42+.47*patch))
soil*=np.clip((clearance+.13)/.4,0,1)
soil=np.maximum(soil,foot_soil)
# The traffic fields also apply inside the placement exclusion for people and
# carts. Only the geometric scatter needs that clearance.
soil[street_patch]=np.maximum(soil[street_patch],bank_earth*street_blend)
church_patch,church_soil,church_stone=chapel_wear(x,y,chapel,noise)
soil[church_patch]=np.maximum(soil[church_patch],church_soil)
rock_edge[church_patch]=np.minimum(rock_edge[church_patch],church_stone)
# The door normal gives each worn threshold its actual position and direction.
# Wider public doors have a turning patch; private doors have a narrower tread.
public_doors={plan[key]['house'] for key in ('blacksmith','carpenter','tavern','herbalist') if key in plan}
for num,shape in house_shapes.items():
    nx,ny=shape['normal']
    dx,dy=x-shape['entry'][0],y-shape['entry'][1]
    along=dx*nx+dy*ny
    across=-dx*ny+dy*nx
    apron=np.hypot((along-1.08)/1.65,across/(2.3 if num in public_doors else 1.25))
    tread=np.clip((1.15-apron+noise*.11)/.46,0,1)*np.clip((along+.05)/.4,0,1)
    soil=np.maximum(soil,tread*(.72+.20*patch))
for area in plan.get('service_clearings',[]):
    if 'soil_weight' in area:
        edge=box_distance(*area['center'],*area['half'],area['yaw'])
        worn=np.clip((.35-edge+noise)/1.10,0,1)*patch*area['soil_weight']
        soil=np.maximum(soil,worn)
# The smith's open front apron spans the masonry-free frontage defined in its
# kit. Leave the rear chimney reservation and the interior unaffected.
smith=plan.get('blacksmith',{})
if 'front_wall_clearance_local_m' in smith:
    house=next(h for h in plan['houses'] if h[0]==smith['house'])
    left,right,near,far=smith['front_wall_clearance_local_m']
    ox,oy=rotate((left+right)*.5,(near+far)*.5,house[5])
    smith_apron=box_distance(house[3]+ox,house[4]+oy,(right-left)*.45,(far-near)*.5,house[5])
    worn=np.clip((.37-smith_apron+noise*.5)/.72,0,1)*(.48+.36*patch)
    soil=np.maximum(soil,worn)
if not plan_only:
    # B gives the common material its metric coarse-road edge. G holds finer
    # trampled earth, also shared by the visible terrain and the RVT writer.
    sdf=Image.fromarray((np.clip(.5-rock_edge/5.,0,1)*255).astype('uint8'))
    turf=protected_turf(x,y,plan,cart_distance,roads,noise,wall_segments,street_patch,church_patch,church_soil)
    for service in plan.get('service_clearings',[]):
        turf*=ramp(box_distance(*service['center'],*service['half'],service['yaw'])/.42)
    if 'front_wall_clearance_local_m' in smith:
        turf*=ramp(smith_apron/.65)
    for house in house_shapes.values():
        turf*=ramp((box_distance(*house['center'],*house['half'],house['angle'])+.06)/.36)
    cover=Image.fromarray((np.clip(turf,0.,1.)*255).astype('uint8'))
    # White alpha also gives older RGB-only road masks an empty turf layer.
    channels=(coverage_image,Image.fromarray((soil*255).astype('uint8')),sdf,Image.fromarray(255-np.asarray(cover)))
    # These are four independent fields, so filter each without alpha premultiplication.
    packed=Image.merge('RGBA',tuple(c.resize((2048,1024),Image.Resampling.LANCZOS) for c in channels))
    packed, verge = dress_ground(packed, cover.resize((460,320),Image.Resampling.BOX), plan, kit)
    (out/'VergeTurf.raw').write_bytes(verge.tobytes())
    packed.save(out/'RoadMaskBase.png')
    apply_ground(packed, plan, kit).save(out/'RoadMask.png')
    if mask_only:
        sys.exit(0)
    plant_image=Image.fromarray((plant_coverage*255).astype('uint8'))
    (out/'PlantExclusion.raw').write_bytes(plant_image.resize((460,320),Image.Resampling.BOX).tobytes())
    # Each output texel stores the minimum of its 20 cm square. Subtracting
    # half the source-pixel diagonal covers positions between the 5 cm samples.
    filtered=minimum_filter(clearance,size=(math.ceil(rows/320)+2,math.ceil(cols/460)+2))
    safe=np.asarray(Image.fromarray(filtered.astype('float32')).resize((460,320),Image.Resampling.NEAREST))-.036
    (out/'DressingClearance.raw').write_bytes(safe.astype('<f4').tobytes())

if '--data-only' in sys.argv:
    sys.exit(0)

# The sheet uses the same axes as the road mask; north is local -Y.
W,H=1640,1040
im=Image.new('RGB',(W,H),'#f4f1e8')
d=ImageDraw.Draw(im)
def font(size,bold=False):
    return ImageFont.truetype('C:/Windows/Fonts/msyh'+('bd' if bold else '')+'.ttc',size)
def title(pos,s,size,col='#293c36',bold=False):
    d.text(pos,s,font=font(size,bold),fill=col,anchor='lm')
left,top,k=70,145,12
def pt(p):return (round(left+(p[0]+ex)*k),round(top+(p[1]+ey)*k))
def disk(pos,r,fill):
    xx,yy=pos; d.ellipse((xx-r,yy-r,xx+r,yy+r),fill=fill)
def line(points,col,width):d.line([pt(p) for p in points],fill=col,width=width,joint='curve')
base=Image.new('RGB',(cols,rows))
field=np.clip(.5+.2*coarse+.08*gaussian_filter(grain,2)*7,0,1)
base=Image.fromarray((np.array([213,216,184])+field[:,:,None]*np.array([16,13,10])).astype('uint8'))
road=Image.new('RGB',base.size,'#a88b68')
base.paste(road,mask=Image.fromarray((coverage*219).astype('uint8')))
im.paste(base.resize((int(2*ex*k),int(2*ey*k)),Image.Resampling.LANCZOS),(left,top))
rng=random.Random(145)
for mx,my,rx,ry in plan['meadows']:
    for t in range(int(rx*ry*7)):
        a=rng.uniform(0,2*math.pi); rr=math.sqrt(rng.random())
        q=(mx+math.cos(a)*rr*rx,my+math.sin(a)*rr*ry)
        u,v=pt(q); shade=rng.choice(['#9fa97e','#acb58d','#889674','#d5cfa0'])
        d.line((u-1,v+2,u,v-1,u+2,v+1),fill=shade,width=2)
for x0,y0 in plan['snags']:
    xx,yy=pt((x0,y0))
    for j in range(8):
        a=rng.uniform(0,6.28); length=rng.uniform(6,16)
        d.line((xx,yy,xx+length*math.cos(a),yy+length*math.sin(a)),fill='#797963',width=2)
for x0,y0 in plan['rubble']:
    for j in range(20):
        u,v=pt((x0+rng.gauss(0,.5),y0+rng.gauss(0,.32)))
        disk((u,v),rng.choice([1,2,3]),rng.choice(['#928879','#767870','#c0af96']))
for yard in plan['yard_walls']:
    for variant,x1,y1,x2,y2,height in yard['pieces']:
        span=[(x1,y1),(x2,y2)]
        line(span,'#4e5145',6)
        line(span,'#788361' if variant.endswith('_Mossy') else '#ae9c85',3)
# The courtyard, gate gap and nave use the same local axes as the runtime assembly.
def chapel_pt(a,b):return (hx+a,hy+b)
court=[chapel_pt(front,opening),chapel_pt(front,side),chapel_pt(back,side),
       chapel_pt(back,-side),chapel_pt(front,-side),chapel_pt(front,-opening)]
d.polygon([pt(q) for q in court],fill='#c9ceac')
line([tuple(chapel['trail']),chapel_pt(-11.45,0)],'#b49a78',17)
line(court,'#797b6c',7)
for q in court:disk(pt(q),5,'#646958')
outline=[chapel_pt(-10,-5.2),chapel_pt(10,-5.2),chapel_pt(10,5.2),chapel_pt(-10,5.2)]
d.polygon([pt(q) for q in outline],fill='#716e67',outline='#4b5048',width=3)
line([chapel_pt(-9.8,0),chapel_pt(9.8,0)],'#d2c7ad',3)
for gx,gy in [(-7.12,11.34),(-4.71,11.88),(-2.49,11.08)]:
    line([chapel_pt(gx-.25,gy),chapel_pt(gx+.25,gy)],'#747366',4)
for num,name,model,hx0,hy0,angle,entry in houses:
    width,half=house_shapes[num]['half']
    def local(a,b):
        xx,yy=rotate(a,b,angle)
        return (hx0+xx,hy0+yy)
    corners=[pt(local(a,b)) for a,b in [(-width,-half),(width,-half),(width,half),(-width,half)]]
    ruin='Ruined' in model
    d.polygon([(u+4,v+5) for u,v in corners],fill='#a7aa8e')
    d.polygon(corners,fill=('#ac9e87' if ruin else '#8c8376'),outline='#4b5048',width=3)
    if ruin:
        d.polygon([pt(local(-2.5,-half+.7)),pt(local(2.5,-half+.7)),pt(local(2.5,half-.7)),pt(local(-2.5,half-.7))],fill='#c6b99c')
        for j in range(19):
            u,v=pt(local(rng.uniform(-2.5,2.5),rng.uniform(-half+.6,half-.6)))
            d.line((u,v,u+4,v+2),fill='#857966',width=2)
    else:
        line([local(0,-half),local(0,half)],'#d2c4ae',2)
        for end in (-half,half):
            line([local(-width,end),local(0,end*.72),local(width,end)],'#b7ab96',2)
    disk(pt(entry),4,'#e8d2a2')
    bx,by=pt((hx0,hy0))
    disk((bx,by),13,'#374b43')
    d.text((bx,by),num,font=font(14,True),fill='#fff8e9',anchor='mm')
def note(pos,s):
    u,v=pt(pos);d.text((u,v),s,font=font(15,True),fill='#484c39',anchor='mm',stroke_width=3,stroke_fill='#e0ddc7')
note((-39,2.8),'谷道入口');note((-8,-15.6),'教堂广场');note((22,-13.4),'旧教堂');note((1,-16.5),'院门');note((33,5.2),'东街')
d.rectangle((left,top,left+2*ex*k,top+2*ey*k),outline='#64705d',width=2)
title((70,43),'温带丘陵   /   教堂与废弃村庄',34,bold=True)
title((71,93),'建筑与道路总平面     ·     Normandy Village',21,'#5a695d')
bx=1220;title((bx,174),'房屋索引',27,bold=True)
for i,(num,name,*_) in enumerate(houses):
    yy=239+i*53
    title((bx,yy),num,18,'#7b806d',True);title((bx+58,yy),name,23)
d.line((bx,610,1568,610),fill='#bfc3b3',width=2)
title((bx,656),'场地  92 × 64 米',22,bold=True)
title((bx,704),'穿村泥路     4.2 米',20)
title((bx,746),'教堂巷      3.1 米',20)
title((bx,788),'教堂院门    3.9 米柱距',20)
for yy,col,label in [(844,'#ae9c85','裸石残墙'),(884,'#788361','苔石残墙')]:
    d.line((bx,yy,bx+41,yy),fill='#4e5145',width=7)
    d.line((bx,yy,bx+41,yy),fill=col,width=3)
    title((bx+58,yy),label,18)
title((bx,936),'浅色圆点标示入户方向',16,'#697565')
y0=964
for i in range(4):
    d.rectangle((left+i*60,y0,left+(i+1)*60,y0+7),fill='#42594c' if i%2==0 else '#c3c6b2')
for i in (0,2,4):title((left+i*60,y0+28),str(i*5)+' m' if i==4 else str(i*5),14)
d.polygon([(1119,975),(1129,942),(1139,975),(1129,969)],fill='#485b4e')
title((1148,962),'北',18)
im.save(out/'Village_Plan.png')
