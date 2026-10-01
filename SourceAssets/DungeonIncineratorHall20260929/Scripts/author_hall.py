"""Precision architecture, not a prop scatter or a production room-pool installation."""
from pathlib import Path
SCRIPT_DIR=Path(__file__).resolve().parent
exec(compile((SCRIPT_DIR/'geometry.py').read_text(encoding='utf-8'),str(SCRIPT_DIR/'geometry.py'),'exec'))
detail.setup(globals())
ROOM['height_m']=8.0
outline=CFG['hall']['outline']
pit=CFG['ash_pit']; px0,py0,px1,py1=pit['rect']

def prism(kind,points,z0,z1,mat='Concrete'):
    # Closed XY extrusion, with outward bottom/top and a single side per edge.
    n=len(points)
    vs=[(x,y,z) for z in (z0,z1) for x,y in points]
    fs=[tuple(reversed(range(n))),tuple(range(n,2*n))]
    fs.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    poly(kind,vs,fs,mat)

def clip_xy(points,axis,value,greater):
    if not points:return []
    out=[];a=points[-1];da=(a[axis]-value)*(1 if greater else -1)
    for b in points:
        db=(b[axis]-value)*(1 if greater else -1)
        if (da>=0)!=(db>=0):
            t=da/(da-db);out.append([a[k]+(b[k]-a[k])*t for k in range(2)])
        if db>=0:out.append(b)
        a,da=b,db
    return out

def patch_floor(x0,y0,x1,y1):
    q=outline
    for axis,value,greater in ((0,x0,True),(0,x1,False),(1,y0,True),(1,y1,False)):
        q=clip_xy(q,axis,value,greater)
    if len(q)>=3:prism('Floors',q,-.25,0)

# Keep an actual hole: the ash pocket has its own lower floor and recovery stairs.
patch_floor(-14,-10.5,px0,10.5)
patch_floor(px1,-10.5,14,10.5)
patch_floor(px0,-10.5,px1,py0)
patch_floor(px0,py1,px1,10.5)
box('AshPit',((px0+px1)/2,(py0+py1)/2,pit['floor']-.14),(px1-px0,py1-py0,.28),'Mortar')
for x in (px0-.09,px1+.09):box('AshPit',(x,(py0+py1)/2,-.6),(.18,py1-py0,1.2))
box('AshPit',((px0+px1)/2,py0-.09,-.6),(px1-px0,.18,1.2))
mid=pit.get('recovery_centre_x',(px0+px1)/2);rw=pit['recovery_width'];run=pit['recovery_steps']*pit['recovery_going']
for i in range(pit['recovery_steps']):
    top=pit['floor']+(i+1)*.15
    box('Stairs',(mid,py1-run+(i+.5)*.30,(pit['floor']-.1+top)/2),(rw,.30,top-pit['floor']+.1),'Concrete')
for lo,hi in ((px0,mid-rw/2),(mid+rw/2,px1)):
    box('AshPit',((lo+hi)/2,py1+.09,-.6),(hi-lo,.18,1.2))
    railings((lo,py1+.08,0),(hi,py1+.08,0))
for x in (px0-.08,px1+.08):railings((x,py0,0),(x,py1,0))
railings((px0,py0-.08,0),(px1,py0-.08,0))
for x in (mid-rw/2-.08,mid+rw/2+.08):
    railings((x,py1-run,pit['floor']+.15),(x,py1,0),height=.98)

# Asymmetric wedge perimeter, real full-size door apertures and closed lintels.
for i,start in enumerate(outline):
    end=outline[(i+1)%len(outline)]
    openings=[]
    if start[0]==end[0] and abs(start[0])==14:
        openings=[dict(center=abs(start[1]),width=3.,height=2.8)]
    wall_segment(start,end,8.6,openings,tiles=i in (3,4,5,6))

# Slightly rising roof, triangular trusses and physically attached perimeter piers.
roof=lambda y:8.6+(y+10.5)*.035
n=len(outline)
vs=[(x,y,roof(y)+dz) for dz in (0,.26) for x,y in outline]
poly('Roof',vs,[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],'Concrete')
for x in (-8.,-2.5,3.,8.):
    beam('RoofTrusses',(x,-10.2,8.15),(x,10.2,8.15),.17,.25,'PaintedSteel')
    beam('RoofTrusses',(x,-10.2,roof(-10.2)-.08),(x,10.2,roof(10.2)-.08),.17,.22,'PaintedSteel')
    for j in range(8):
        y=-10.2+j*2.55
        beam('RoofTrusses',(x,y,8.15 if j%2==0 else roof(y)-.08),
             (x,y+2.55,roof(y+2.55)-.08 if j%2==0 else 8.15),.075,.075,'BareSteel')
    for y in (-10.28,10.28):
        box('Columns',(x,y,4.),(.42,.45,8.),'Concrete')
        box('Columns',(x,y,.16),(.6,.57,.32),'Concrete')

# Three cold masonry furnace bays. Detailed doors/drives remain replaceable by bay.
f=CFG['furnaces'];back,front=f['body_y'];h=f['height'];width=f['bay_width'];door=f['opening_width']
for index,x in enumerate(f['centres_x']):
    side=(width-door)/2
    for dx in (-door/2-side/2,door/2+side/2):
        box('FurnaceMasonry',(x+dx,(back+front)/2,h/2),(side,front-back,h),'Mortar')
    box('FurnaceMasonry',(x,(back+front)/2,(2.95+h)/2),(door,front-back,h-2.95),'Mortar')
    box('FurnaceMasonry',(x,(back+front)/2,.175),(door,front-back,.35),'Mortar')
    box('FurnaceMasonry',(x,back+.14,1.65),(door,.28,2.6),'Concrete')
    # Recessed cold door leaves have depth, border rails and hinge barrels; no animation.
    box('FurnaceDoors',(x,front-.34,1.65),(door-.10,.16,2.5),'PaintedSteel')
    for dx in (-door/2-.045,door/2+.045):
        box('FurnaceDoorFrames',(x+dx,front+.025,1.65),(.09,.21,2.78),'BareSteel')
    for z in (.215,3.085):box('FurnaceDoorFrames',(x,front+.025,z),(door+.18,.21,.09),'BareSteel')
    for dx in (-.95,.95):
        for z in (.8,2.4):detail.tube('FurnaceDetails',[(x+dx,front-.10,z-.14),(x+dx,front-.10,z+.14)],.07,'BareSteel',20)
    box('FurnaceDetails',(x,front-.23,1.95),(.58,.065,.32),'Rubber')
    for dx in (-.37,.37):box('FurnaceDetails',(x+dx,front-.05,1.43),(.045,.30,.05),'BareSteel')
    detail.tube('FurnaceDetails',[(x-.37,front+.07,1.43),(x+.37,front+.07,1.43)],.028,'BareSteel',16)
    # Fixed loading sill with a shallow open trough, no fake moving conveyor machinery.
    length=f['loading_length'];cy=front+length/2
    box('LoadingTroughs',(x,cy,.65),(1.8,length,.14),'BridgeDeck')
    for dx in (-.87,.87):box('LoadingTroughs',(x+dx,cy,.86),(.065,length,.34),'BareSteel')
    for yy in (front+.32,front+length-.25):
        for dx in (-.65,.65):box('LoadingSupports',(x+dx,yy,.29),(.12,.12,.58),'PaintedSteel')
    # Extraction ducts terminate in the roof, with collars and a proper collector hood.
    box('ExhaustHoods',(x,(back+front)/2,h+.28),(width-.25,front-back-.12,.56),'PaintedSteel')
    detail.smooth_pipe([(x,-8.7,h+.56),(x,-8.7,6.7),(x,-7.9,6.7),(x,-7.9,roof(-7.9)+.07)],.39)
    for z in (5.7,7.65):box('Frames',(x,-9.8,z),(.12,1.3,.12),'BareSteel')
    # Floor loading tracks identify each bay without filling the seven-metre aisle.
    for dx in (-.72,.72):box('FloorGuides',(x+dx,-5.9,.015),(.05,2.5,.03),'RailSteel')

# Observation gallery with two opposing wide stairs: a walkable return loop.
o=CFG['observation'];x0,x1=o['x'];y0,y1=o['y'];top=o['top'];sy=o['stairs_centre_y'];sw=o['stairs_width']
box('ObservationDeck',((x0+x1)/2,(y0+y1)/2,top-.12),(x1-x0,y1-y0,.24),'BridgeDeck')
for x in (-6.8,0,6.8):
    for y in (y0+.18,y1-.18):
        box('ObservationSupports',(x,y,(top-.24)/2),(.18,.18,top-.24),'PaintedSteel')
        box('ObservationSupports',(x,y,.03),(.34,.34,.06),'BareSteel')
    beam('ObservationSupports',(x,y0,top-.32),(x,y1,top-.32),.20,.24,'BareSteel')
railings((x0,y0+.06,top),(x1,y0+.06,top))
railings((x0,y1-.05,top),(x1,y1-.05,top))
for sign in (-1,1):
    landing=sign*7.;foot=sign*(7.+o['steps']*o['going'])
    for i in range(o['steps']):
        x=foot-sign*(i+.5)*o['going'];zt=(i+1)*o['rise']
        box('Stairs',(x,sy,zt-.055),(o['going'],sw,.11),'BridgeDeck')
        box('Stairs',(x+sign*.14,sy,zt-.13),(.02,sw,.15),'PaintedSteel')
        box('StairNosing',(x+sign*.12,sy,zt+.004),(.035,sw-.04,.008),'Yellow')
    for y in (sy-sw/2+.08,sy+sw/2-.08):
        beam('ObservationSupports',(foot,y,-.05),(landing,y,top-.1),.14,.20,'PaintedSteel')
        railings((foot,y,.15),(landing,y,top))
    railings((landing,sy+sw/2+.03,top),(landing,y1-.05,top))
    # Short side frontage below the stair mouth, without barring the landing.
    if sy-sw/2-y0>.04:railings((landing,y0+.06,top),(landing,sy-sw/2-.02,top))

# Actual vestibules and independent sample-only closures at the compatible ports.
for sign in (-1,1):
    a,b=sorted((sign*14.,sign*16.))
    box('Floors',((a+b)/2,0,-.125),(b-a,4.5,.25))
    wall_segment((a,-2.25),(b,-2.25),3.4,tiles=False)
    wall_segment((b,2.25),(a,2.25),3.4,tiles=False)
    x=sign*16
    wall_segment((x,-2.25),(x,2.25),3.4,[dict(center=2.25,width=3.,height=2.8)],tiles=False)
    box('Roof',((a+b)/2,0,3.53),(b-a+.28,4.78,.26))
    box('SamplePortCaps',(x+sign*.09,0,1.4),(.14,3.,2.8),'PaintedSteel')

# Main service run and physically suspended fixtures, all outside the working aisle.
detail.smooth_pipe([(-12.8,9.85,3.4),(-12.8,9.85,7.45),(8.4,9.85,7.45)],.11)
for lamp in CFG['lights']:
    x,y,z=lamp['position'];ceiling=3.4 if abs(x)>14 else roof(y)
    for dx in (-.46,.46):
        detail.tube('Frames',[(x+dx,y,z+.19),(x+dx,y,ceiling-.01)],.014,'BareSteel',12)
        box('Frames',(x+dx,y,ceiling-.022),(.1,.12,.04),'BareSteel')

if not globals().get('SKIP_HALL_EXPORT',False):
    exec(compile((SCRIPT_DIR/'export_geometry.py').read_text(encoding='utf-8'),str(SCRIPT_DIR/'export_geometry.py'),'exec'))
