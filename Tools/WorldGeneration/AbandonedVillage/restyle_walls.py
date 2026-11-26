"""Fit intact demo assemblies to village boundaries without stretching fragments."""
import json
import math
import random
from pathlib import Path
from layout_geometry import house_geometry, house_paths, rotate
from wall_support import fit_plan

root=Path(__file__).resolve().parents[3]
folder=root/'SourceAssets/TemperateHillsVillage'
plan=json.loads((folder/'layout.json').read_text(encoding='utf-8'))
plan['house_scale']=1.2
for house in plan['houses']:
    if house[0]=='04':house[5]=97
kit=json.loads((folder/'house-pieces.json').read_text(encoding='utf-8'))
reference=json.loads((folder/'DemoRevision20261114/wall-patterns.json').read_text())
meshes=reference['meshes']
patterns=reference['patterns']
scale=.8
rng=random.Random(2026111402)
shapes=[house_geometry(h,kit[h[2]],plan['house_scale']) for h in plan['houses']]
paths=[(r['points'],r['width']) for r in plan['roads']]+house_paths(plan,kit)
walls=[]
placed=[]
used=[]
chapel=plan['chapel'];cx,cy=chapel['center'];front,back,side,_=chapel['yard']

def distance(p,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]
    t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy)))
    return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)

def clear(p,existing,width=.65):
    x,y=p
    if abs(x)>plan['extent_m'][0]-width-.2 or abs(y)>plan['extent_m'][1]-width-.2:return False
    if cx+front-width-.25<x<cx+back+width+.25 and cy-side-width-.25<y<cy+side+width+.25:return False
    for shape in shapes:
        dx,dy=rotate(x-shape['center'][0],y-shape['center'][1],-shape['angle'])
        if abs(dx)<shape['half'][0]+width+.25 and abs(dy)<shape['half'][1]+width+.25:return False
    for line,w in paths:
        if any(distance(p,a,b)<w*.5+width+.2 for a,b in zip(line,line[1:])):return False
    if any(math.dist(p,q)<1.1+width for q in plan['rubble']):return False
    # Adjacent yards share one boundary; do not leave a narrow double-wall alley.
    return not any(distance(p,a,b)<1.25+width for a,b in existing)

def placement(pattern,center,yaw):
    result=[]
    for part in pattern['parts']:
        lo,hi=meshes[part['mesh']]['bounds']
        dx,dy=rotate(part['pos'][0]*scale,part['pos'][1]*scale,yaw)
        pos=[center[0]*100+dx,center[1]*100+dy,part['pos'][2]*scale]
        rotation=[part['rot'][0],part['rot'][1]+yaw,part['rot'][2]]
        ox,oy=rotate((lo[0]+hi[0])*scale*.5,(lo[1]+hi[1])*scale*.5,rotation[1])
        midpoint=((pos[0]+ox)/100,(pos[1]+oy)/100)
        half=(hi[0]-lo[0])*scale/200
        ex,ey=rotate(half,0,rotation[1])
        a=(midpoint[0]-ex,midpoint[1]-ey);b=(midpoint[0]+ex,midpoint[1]+ey)
        width=(hi[1]-lo[1])*scale/200
        meta=dict(mesh=meshes[part['mesh']]['path'],pos=pos,rot=rotation,scale=[scale]*3,
                  materials=part['materials'],half_width_m=width,source_index=part['source_index'])
        segment=[part['mesh'].split('Piece')[-1],*a,*b,(pos[2]+hi[2]*scale)/100]
        result.append((segment,meta))
    return result

def native_clear(items,existing):
    for piece,meta in items:
        a,b=piece[1:3],piece[3:5]
        steps=max(2,math.ceil(math.dist(a,b)/.35))
        for i in range(steps+1):
            p=[a[j]+(b[j]-a[j])*i/steps for j in (0,1)]
            if not clear(p,existing,meta['half_width_m']):return False
    return True

def emit_run(a,b,group,existing):
    length=math.dist(a,b)
    yaw=math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]))
    cursor=.08;last=-1;assemblies=0
    while length-cursor>1.25:
        remaining=length-cursor
        choices=[]
        for i,p in enumerate(patterns):
            span=p['length_cm']*scale/100
            if span>remaining or i==last or p['width_cm']*scale>95:continue
            if len(p['parts'])==1 and 'PieceC' in p['parts'][0]['mesh']:continue
            # Reject steep source-terrain assemblies that would bury a whole part on our flat pad.
            if any(part['pos'][2]+meshes[part['mesh']]['bounds'][1][2]<55 for part in p['parts']):continue
            choices.append((i,p,span))
        rng.shuffle(choices)
        choices.sort(key=lambda value:len(value[1]['parts'])==1)
        selected=None
        for i,p,span in choices:
            t=(cursor+span*.5)/length
            center=[a[j]+(b[j]-a[j])*t for j in (0,1)]
            items=placement(p,center,yaw+(180 if rng.random()<.4 else 0))
            if native_clear(items,existing):
                selected=(i,span,items);break
        if selected is None:
            cursor+=.4;continue
        index,span,items=selected
        for piece,meta in items:
            group['pieces'].append([piece[0],*[round(v,4) for v in piece[1:]]])
            group['native_instances'].append(meta)
        group['source_patterns'].append(index);used.append(index)
        placed.append(([a[j]+(b[j]-a[j])*cursor/length for j in (0,1)],
                       [a[j]+(b[j]-a[j])*(cursor+span)/length for j in (0,1)]))
        last=index;assemblies+=1
        # Occasional surviving gaps, rather than the same small break after every module.
        cursor+=span+(rng.uniform(.45,.95) if assemblies%3==0 else -.10)

def add_line(name,points,roadside=False):
    group=dict(name=name,roadside=roadside,pieces=[],native_instances=[],source_patterns=[])
    existing=list(placed)
    for a,b in zip(points,points[1:]):
        count=max(1,math.ceil(math.dist(a,b)/.12));start=None
        for i in range(count+1):
            point=[a[j]+(b[j]-a[j])*i/count for j in (0,1)]
            allowed=clear(point,existing)
            if allowed and start is None:start=point
            if start is not None and (not allowed or i==count):
                end=point if allowed else [a[j]+(b[j]-a[j])*(i-1)/count for j in (0,1)]
                if math.dist(start,end)>1.4:emit_run(start,end,group,existing)
                start=None
    if group['pieces']:walls.append(group)

def offset_road(points,amount):
    result=[]
    for i,p in enumerate(points):
        a,b=points[max(0,i-1)],points[min(len(points)-1,i+1)];length=math.dist(a,b)
        result.append([p[0]-(b[1]-a[1])*amount/length,p[1]+(b[0]-a[0])*amount/length])
    return result

main=plan['roads'][0]
for sign,label in ((-1,'北侧'),(1,'南侧')):
    add_line('主街'+label+'原生残墙',offset_road(main['points'],sign*(main['width']*.5+1.35)),True)

# Three-sided property boundaries with varied setbacks. The street already forms the front boundary.
for house,shape in zip(plan['houses'],shapes):
    cxh,cyh=shape['center'];hx,hy=[v+rng.uniform(1.9,2.5) for v in shape['half']]
    corners=[(-hx,-hy),(hx,-hy),(hx,hy),(-hx,hy)]
    front_side=max(range(4),key=lambda i:sum(n*v for n,v in zip(shape['normal'],rotate(*[(corners[i][j]+corners[(i+1)%4][j])*.5 for j in (0,1)],shape['angle']))))
    points=[]
    for step in range(4):
        local=corners[(front_side+1+step)%4];dx,dy=rotate(*local,shape['angle'])
        points.append([cxh+dx,cyh+dy])
    add_line(house[1]+'共享院界',points)
add_line('旧果园残留边界',[[-39,-22],[-38,-24],[-30,-24]])
plan['yard_walls']=walls
plan['wall_placement_version']=2
plan['wall_reference']=dict(source=reference['source'],source_instances=reference['source_count'],
                            uniform_assembly_scale=scale,unique_patterns=len(set(used)))
fit_plan(plan)
(folder/'layout.json').write_text(json.dumps(plan,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
report=dict(instances=sum(len(w['pieces']) for w in walls),assemblies=len(used),unique_patterns=len(set(used)),
            boundaries=len(walls),uniform_scale=scale,source_instances=reference['source_count'])
(folder/'DemoRevision20261114/wall-authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('VILLAGE_DEMO_WALL_LAYOUT',json.dumps(report))
