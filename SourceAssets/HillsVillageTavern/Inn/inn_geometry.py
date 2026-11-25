"""Tavern upper storeys, house-local centimetres. +Y points into the garden."""
from pathlib import Path
import sys
import math
import random

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Tools/WorldGeneration/VillageBakery'))
from shell_geometry import Mesh, skin

WEST, EAST, FRONT, BACK = -724, 644, -426, 828
GUEST, OWNER, EAVES = 340, 642, 958
# y, door x, floor height, inward yaw: each socket faces into its own room.
DOORS = [(side*83, x, GUEST, side*90) for side in (-1, 1) for x in (-146, 319)]
DOORS += [(-83, -145, OWNER, -90)]

def cut_wall(mesh,axis,line,start,end,z0,z1,holes,mat,thick):
    heights=sorted({z0,z1,*[v for _,_,a,b in holes for v in (a,b)]})
    for bottom,top in zip(heights,heights[1:]):
        cursor=start
        gaps=sorted((a,b) for a,b,low,hi in holes if low<top and hi>bottom)
        for a,b in gaps+[(end,end)]:
            if a>cursor:
                if hasattr(mesh,'panels'):
                    mesh.panels.append((axis,line,cursor,a,bottom,top,thick))
                skin(mesh,axis,line,cursor,a,bottom,top,mat,thick*.47 if hasattr(mesh,'panels') else thick)
            cursor=b

def facade(wall,trim,axis,line,start,end,z0,z1,windows,front):
    holes=[(x-54,x+54,z0+92,z0+218) for x in windows]
    cut_wall(wall,axis,line,start,end,z0,z1,holes,'Masonry',27)
    point=lambda a,z:(a,line,z) if axis=='X' else (line,a,z)
    for z in (z0+6,z1-7):
        trim.timber('DarkWood',point(start,z),point(end,z),24,14)
    for x in windows:
        for z in (z0+91,z0+219):
            skin(trim,axis,line,x-60,x+60,z-4,z+4,'Oak',26)
        # Deep sill, central mullion and a divided upper light, open to daylight.
        skin(trim,axis,line,x-57,x+57,z0+84,z0+91,'Sawn',32)
        skin(trim,axis,line,x-2.5,x+2.5,z0+92,z0+218,'Oak',9)
        skin(trim,axis,line,x-54,x+54,z0+176,z0+181,'Oak',9)
    for x in windows:
        for at in (x-58,x+58):
            skin(trim,axis,line,at-4,at+4,z0+87,z0+223,'DarkWood',39)
def floors(mesh,z,hole,seed):
    rng=random.Random(seed)
    left,right,front,back=WEST+3,EAST-2,FRONT+3,BACK-2
    hx0,hx1,hy0,hy1=hole
    # Continuous underside carries collision. Boards above have staggered butt joints.
    rectangles=[(left,hx0,front,back),(hx1,right,front,back),
                (hx0,hx1,front,hy0),(hx0,hx1,hy1,back)]
    # Mason's shaft runs from the original kitchen hood through both ceilings.
    def shaft(rect):
        x0,x1,y0,y1=rect
        if x1<=548 or x0>=614 or y1<=48 or y0>=110:return [rect]
        return [(x0,min(x1,548),y0,y1),(max(x0,614),x1,y0,y1),
                (max(x0,548),min(x1,614),y0,min(y1,48)),
                (max(x0,548),min(x1,614),max(y0,110),y1)]
    for rect in rectangles:
        for x0,x1,y0,y1 in shaft(rect):
            if min(x1-x0,y1-y0)<1:continue
            mesh.box('DarkWood',x0,x1,y0,y1,z-13,z-3)
            n=max(1,round((y1-y0)/23))
            for i in range(n):
                lo=y0+(y1-y0)*i/n+.16
                hi=y0+(y1-y0)*(i+1)/n-.16
                p=x0
                span=rng.uniform(105,330)
                while p<x1-.3:
                    q=min(x1,p+span)
                    mesh.box('Sawn' if rng.random()<.12 else 'Oak',p,q-.12,lo,hi,z-3.1,z,.22)
                    p=q;span=rng.uniform(240,410)

def divider(mesh,join,axis,pos,start,end,z,head,doors):
    holes=[(x-55,x+55,z,z+221) for x in doors]
    cut_wall(mesh,axis,pos,start,end,z,head,holes,'Masonry',18)
    cursor=start
    for at in sorted(doors):
        skin(join,axis,pos,cursor,at-55,z+2,z+11,'Oak',13)
        cursor=at+55
    skin(join,axis,pos,cursor,end,z+2,z+11,'Oak',13)
    for x in doors:
        for at in (x-58,x+58):
            skin(join,axis,pos,at-4,at+4,z,z+226,'DarkWood',15)
        skin(join,axis,pos,x-61,x+61,z+220,z+229,'DarkWood',16)

def stair(stairs, rails, x, start, end, z0,z1,count):
    half=80
    dz=(z1-z0)/count; dy=(end-start)/count
    for i in range(count):
        y=start+i*dy; next_y=y+dy; z=z0+(i+1)*dz
        a,b=sorted((y,next_y))
        # Hand-worn leading edge is a shallow bevel, dark end grain stays below.
        stairs.box('Oak',x-half,x+half,a,b,z-dz-2,z-.9,.9)
        stairs.box('Sawn',x-half-1,x+half+1,a-.8,b+.8,z-3.5,z,1.1)
    for xx in (x-half,x+half):
        stairs.timber('DarkWood',(xx,start,z0-9),(xx,end,z1-11),12,18)
    side=x+half
    for t in (0,.25,.5,.75,1):
        y=start+t*(end-start);z=z0+t*(z1-z0)
        rails.box('DarkWood',side-3.2,side+3.2,y-3.2,y+3.2,z,z+92,.55)
    rails.timber('Oak',(side,start,z0+90),(side,end,z1+90),8,7)

def balcony_rail(m,x,y0,y1,z):
    for i in range(6):
        y=y0+(y1-y0)*i/5
        m.box('Oak',x-3,x+3,y-3,y+3,z,z+94,.7)
    m.timber('DarkWood',(x,y0,z+92),(x,y1,z+92),8,7)

def upper_wall_runs():
    for z,top in ((GUEST,OWNER),(OWNER,EAVES)):
        for axis,line,start,end,windows in (
            ('X',FRONT,WEST,EAST,[-520,-138,320,525] if z==GUEST else [-512,-175,214,494]),
            ('X',BACK,WEST,EAST,[-466,-115,300,504] if z==GUEST else [-510,-162,182,433]),
            ('Y',WEST,FRONT,BACK,[-200,185,633]),('Y',EAST,FRONT,BACK,[-240,244,633])):
            if z==OWNER and axis=='Y':
                yield axis,line,start,423,z,top,windows[:-1]
                yield axis,line,423,end,z,872,[633]
            else:
                yield axis,line,start,end,z,872 if z==OWNER and line==BACK else top,windows

def make_models(hall_refit=False,joinery=False):
    if joinery:
        import suite_geometry
    build_face=suite_geometry.facade if joinery else facade
    outer,wood,deck,stairs,inside,rails,flue,leaf=[Mesh() for _ in range(8)]
    outer.panels=[];inside.panels=[]
    ramp=Mesh()
    # Rear service range starts behind the old counter; its tiled roof falls to the garden.
    for axis,line,lo,hi,windows in [('X',BACK,WEST,EAST,[-452,-95,310]),('Y',WEST,422,BACK,[633]),('Y',EAST,422,BACK,[652])]:
        build_face(outer,wood,axis,line,lo,hi,-8,GUEST,windows,False)
    for axis,line,start,end,z,top,windows in upper_wall_runs():
        build_face(outer,wood,axis,line,start,end,z,top,windows,line in (WEST,FRONT))
        if axis=='Y' and z==OWNER and start==423:
            outer.prism('Masonry',[(line-5,423,871),(line-5,423,969),(line-5,end,871)],(10,0,0))
            outer.panels.append(('Y',line,423,end,871,969,27))
    # Lower stone heads finish around +324. A continuous oak bressummer seats the upper frame.
    for axis,line,s,e in [('X',FRONT,WEST,EAST),('X',BACK,WEST,EAST),('Y',WEST,FRONT,BACK),('Y',EAST,FRONT,BACK)]:
        skin(wood,axis,line,s,e,315,340 if joinery else 341,'DarkWood',30)
    # The public stair is stacked. The gallery on its east side connects the full landings.
    x=-617; start=-40; end=551
    for z,lo,count in [(GUEST,0,22),(OWNER,GUEST,20)]:
        floors(deck,z,(-708,-524,start,end),472+z)
        stair(stairs,rails,x,start,end,lo,z,count)
        ramp.prism('Oak',[(x-82,start,lo-8),(x-82,end,z-8),(x-82,end,z),(x-82,start,lo)],(164,0,0))
        balcony_rail(rails,-524,start,end,z)
        if z==OWNER:
            rails.timber('Oak',(-705,start,z+92),(-524,start,z+92),8,7)
    # Worn planking continues through the previous garden wall at a level threshold.
    for i in range(18):
        a=420+i*22.8
        deck.box('Oak' if i%5 else 'Sawn',WEST+3,EAST-3,a,a+22.7,-11,-2)
    for y in (478,661,811):
        wood.timber('DarkWood',(-508,y,322),(EAST-8,y,322),17,19)
    if joinery:
        del inside.panels
        suite_geometry.rooms(inside)
    elif hall_refit:
        import hall_plan
        hall_plan.partitions(inside,wood,divider,FRONT,BACK,EAST,GUEST,OWNER,EAVES)
    else:
        # Keep the rear guest bedrooms private where the old outside wall became a gallery.
        divider(inside,wood,'X',413,-333,EAST-9,GUEST,OWNER-13,[])
        for side in (-1,1):
            divider(inside,wood,'X',side*83,-333,EAST-9,GUEST,OWNER-13,[-146,319])
            y0,y1=(-416,-83) if side==-1 else (83,413)
            divider(inside,wood,'Y',-333,y0,y1,GUEST,OWNER-13,[])
            divider(inside,wood,'Y',75,y0,y1,GUEST,OWNER-13,[])
        # Third floor: one private bedroom, and a study and dining room off the landing.
        divider(inside,wood,'X',-83,-333,95,OWNER,EAVES,[-145])
        divider(inside,wood,'Y',-333,-416,-83,OWNER,EAVES,[])
        divider(inside,wood,'Y',95,-416,-83,OWNER,EAVES,[])
    for a,b,c,d in [(548,614,48,55),(548,614,103,110),(548,555,55,103),(607,614,55,103)]:
        flue.box('Stone',a,b,c,d,315,1266,.8)
    # The chimney inside the kitchen carries the same stone quoin and mortar finish upstairs.
    for z in (341,642,955):
        for a,b,c,d in [(545,617,45,54),(545,617,104,113),(545,554,54,104),(608,617,54,104)]:
            flue.box('Stone',a,b,c,d,z,z+8,1.1)
    # Leaf is local X-normal, +Y across. Existing door actor supplies hinge and replication.
    for i in range(5):
        leaf.box('Oak',-2,2,-52+i*20.8+.1,-52+(i+1)*20.8-.1,0,216,.45)
    for z in (33,173):leaf.box('DarkWood',1.8,5,-50,50,z,z+11,.9)
    leaf.timber('DarkWood',(4,-44,44),(4,44,172),8,5)
    for z in (43,162):leaf.box('Iron',-3.3,-1.8,-51,-19,z,z+3,.45)
    leaf.box('Iron',-4.8,6.3,34,41,94,103,.7)
    models=dict(WalkRamp=ramp,Facade=outer,TimberFrame=wood,Floors=deck,Stairs=stairs,Partitions=inside,
                Rails=rails,FlueShaft=flue,RoomDoor=leaf)
    if joinery:
        models.update(suite_geometry.fixtures())
    elif hall_refit:models['KitchenPass']=hall_plan.kitchen(cut_wall)
    return models
