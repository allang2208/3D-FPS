"""Precise industrial room modelling using the approved corridor surface library."""
import os, json, math, random, sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'DungeonRailCart20260923/Scripts'))
from rail_geometry import freight as freight_guardrails
from pallet_jack import build as build_pallet_jack
sys.path.insert(0,str(ROOT.parent/'DungeonFreightDoor20260923/Scripts'))
from door_geometry import build as build_freight_door, export_lift
LIB=ROOT.parent/'DungeonRoomShells20260922/Scripts/author_rooms.py'
os.environ['DUNGEON_AUTHOR_ROOT']=str(ROOT)
# Load only the library definitions. Never execute the old room generation loop.
source=LIB.read_text(encoding='utf-8').split('for index,room in enumerate(CFG[\'rooms\']):',1)[0]
H={'__file__':str(LIB),'__name__':'room_author_library'}
exec(compile(source,str(LIB),'exec'),H)
box,poly,tube,bar,detail=(H[k] for k in ('box','poly','tube','bar','detail'))

def material(key,path):
    H['MAPPING'][key]=path
    H['MATS'][key]=bpy.data.materials.new('RS_'+key)
material('Rubber','/Game/Dungeons/AtmosphereV2/RoomInteriors/Materials/M_Room_Rubber')
material('YellowPaint','/Game/Dungeons/AtmosphereV2/RoomInteriors/Materials/M_Room_YellowPaint')
material('Timber','/Game/Dungeons/AtmosphereV2/RoomInteriors/Materials/M_Room_Timber')

def slab_polygon(points,z,thickness,kind):
    n=len(points);vs=[(x,y,zz) for zz in (z-thickness,z) for x,y in points]
    faces=[]
    for tri in tessellate_polygon([[Vector((x,y,0)) for x,y in points]]):
        indices=list(tri)
        faces.extend([tuple(reversed(indices)),tuple(i+n for i in indices)])
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    poly(kind,vs,faces,'Concrete')

def frame_rect(x0,y0,x1,y1,z,width=.07,depth=.07,mat='BareSteel',kind='Equipment'):
    for a,b in [((x0,y0,z),(x1,y0,z)),((x1,y0,z),(x1,y1,z)),((x1,y1,z),(x0,y1,z)),((x0,y1,z),(x0,y0,z))]:
        bar(kind,a,b,width,depth,mat)

def panel_x(x,y,z,w,h,mat='ServicePaint',kind='Equipment'):
    box(kind,(x,y,z),(.065,w,h),mat)
    for yy in (y-w/2+.06,y+w/2-.06):
        for zz in (z-h/2+.07,z+h/2-.07):detail.fastener((x-.04,yy,zz),(-1,0,0),.010,kind=kind)
    tube(kind,[(x-.10,y+.22,z-.12),(x-.17,y+.22,z-.12),(x-.17,y+.22,z+.12),(x-.10,y+.22,z+.12)],.015,'BareSteel')
    for zz in [z-h*.28+i*.065 for i in range(5)]:box(kind,(x-.041,y-.1,zz),(.012,w*.53,.015),'Rubber')

def duct(a,b,width=.8,height=.52):
    a,b=Vector(a),Vector(b);d=b-a;length=d.xy.length;n=max(1,math.ceil(length/1.4))
    bar('Ducts',a,b,width,height,'ServicePaint')
    side=Vector((-d.y,d.x,0)).normalized()
    for i in range(n+1):
        p=a+d*i/n
        bar('Ducts',p-side*(width/2+.018),p+side*(width/2+.018),.05,height+.032,'BareSteel')
        if i in (0,n) or i%2==0:
            for sign in (-1,1):
                q=p+side*sign*(width/2+.09)
                top=detail.ceiling_at(q)
                tube('Ducts',[(q.x,q.y,p.z-height/2-.045),(q.x,q.y,top)],.009,'BareSteel',12)
            bar('Ducts',p-side*(width/2+.16)+Vector((0,0,-height/2-.05)),p+side*(width/2+.16)+Vector((0,0,-height/2-.05)),.05,.05,'BareSteel')

def fan(x,y,z):
    # Recessed steel fan cowl, impeller and true protective grid.
    detail.ring((x,y,z),(1,0,0),.96,.82,.18,'ServicePaint',64,kind='Equipment')
    detail.ring((x+.10,y,z),(1,0,0),.84,.80,.04,'BareSteel',64,kind='Equipment')
    tube('Equipment',[(x-.32,y,z),(x+.04,y,z)],.17,'BareSteel',40)
    for i in range(9):
        a=i*math.tau/9
        vs=[]
        for r,ang,xx in [(.2,a,x),(.73,a+.12,x-.04),(.75,a+.47,x-.17),(.23,a+.59,x-.12)]:
            vs.append((xx,y+r*math.cos(ang),z+r*math.sin(ang)))
        poly('Equipment',vs,[(0,1,2,3),(3,2,1,0)],'PaintedSteel')
    for v in [-.72+i*.12 for i in range(13)]:
        half=math.sqrt(.79**2-v**2)
        tube('Equipment',[(x+.15,y+v,z-half),(x+.15,y+v,z+half)],.008,'BareSteel',12)
        tube('Equipment',[(x+.158,y-half,z+v),(x+.158,y+half,z+v)],.008,'BareSteel',12)
    for i in range(8):
        a=i*math.tau/8
        detail.fastener((x+.12,y+.90*math.cos(a),z+.90*math.sin(a)),(1,0,0),.015,kind='Equipment')

def cable_run(points):tube('Services',points,.008,'Rubber',12)

def pallet(x,y,z,yaw=0):
    def part(dx,dy,dz,size,mat):
        c,s=math.cos(yaw),math.sin(yaw)
        box('Props',(x+dx*c-dy*s,y+dx*s+dy*c,z+dz),size,mat,yaw)
    for dx in (-.43,0,.43):part(dx,0,.08,(.12,1.25,.16),'Timber')
    for j in range(7):part(0,-.56+j*.185,.185,(1.15,.14,.05),'Timber')

def rack(x,y,z=0):
    for dx in (-.7,.7):
        for dy in (-.42,.42):box('Props',(x+dx,y+dy,z+.7),(.055,.055,1.4),'ServicePaint')
    for zz in (.16,.78,1.38):box('Props',(x,y,z+zz),(1.52,.92,.045),'PaintedSteel')
    bar('Props',(x-.7,y+.42,z+.2),(x+.7,y+.42,z+1.3),.025,.025,'BareSteel')
    for dx in (-.37,.32):
        box('Props',(x+dx,y,z+.42),(.53,.67,.45),'ServicePaint')
        box('Props',(x+dx,y-.342,z+.43),(.18,.014,.07),'BareSteel')

def ventilation():
    room=H['ROOM'];p=room['footprint']
    core_offset=room.get('core_offset_x',0.0)
    slab_polygon(p,0,.22,'Floors');slab_polygon(p,4.28,.18,'Ceilings')
    H['slab']([.12,2,1,14,3.2],'Ceilings',True)
    box('Core',(9,8,.18),(6,8,.36),'Concrete')
    box('Core',(8.64,8,2.22),(5.22,7.8,3.76),'PaintedSteel')
    for y in (4.06,11.94):box('Core',(9,y,2.22),(6,.12,3.76),'ServicePaint')
    box('Core',(11.86,8,3.52),(.3,7.78,1.16),'ServicePaint')
    for y in (4.12,8,11.88):box('Core',(11.87,y,1.69),(.26,.18,2.67),'ServicePaint')
    for y in (6.05,9.95):
        # Backing is behind the visible fan, rather than an opaque face across its opening.
        box('Core',(11.12,y,1.7),(.08,3.65,2.65),'Rubber')
        fan(11.89,y,1.69)
    for y in (4.95,6.95,8.95,10.95):panel_x(5.98,y,1.81,1.80,2.52)
    for x in (6.05,11.95):
        box('Core',(x,8,.43),(.1,7.9,.12),'BareSteel')
        box('Core',(x,8,3.91),(.1,7.9,.14),'BareSteel')
    for y in (4.12,11.88):
        for x in (6.2,7.7,9.2,10.7,11.8):detail.fastener((x,y,.37),(0,0,1),.018,kind='Core')
    duct((9+core_offset,8,3.74),(17.8,8,3.74),1.15,.52)
    duct((9+core_offset,6,3.63),(1.05,6,3.63),.85,.46)
    for x in (5.55,12.48):
        for j in range(7):box('Ducts',(x+core_offset+j*.025,6 if x<6 else 8,3.63 if x<6 else 3.74),(.012,.87 if x<6 else 1.17,.49 if x<6 else .55),'Rubber')
    # Filter storage against the outside wall, clear of the ring route.
    rack(1.12,10)
    for i in range(4):
        box('Props',(.9,9.7+i*.17,1.09),(.65,.08,.52),'BareSteel')
        for j in range(9):box('Props',(.59+j*.077,9.69+i*.17,1.09),(.008,.012,.45),'Rubber')
    for y in (4.95,8.95):
        detail.ring((5.84,y,2.53),(-1,0,0),.09,.078,.025,'BareSteel',40,kind='Equipment')
        tube('Equipment',[(5.84,y,2.53),(5.83,y,2.53)],.078,'IvoryTile',32)
        tube('Equipment',[(5.82,y,2.53),(5.82,y+.041,2.57)],.003,'BareSteel',12)
    cable_run([(5.84,4.75,2.47),(5.78,4.75,.52),(5.78,11.5,.52),(5.85,11.5,2.5)])
    # Move the complete rigid machine assembly in the authored mesh, including its
    # fan guards, feet, gauges and cables. Wall fixtures stay put; ducts above are
    # rebuilt between the moved machine and their original wall termination.
    if core_offset:
        for kind in ('Core','Equipment','Services'):
            g=H['GROUPS'].get(kind)
            if g:g['v']=[(v[0]+core_offset,v[1],v[2]) for v in g['v']]

def freight():
    room=H['ROOM']
    for rect in room['floors']:H['slab'](rect,'Floors')
    # Enclose the dock underside; its concrete body provides collision below the top slab.
    box('Dock',(9,16,.19),(18,4,.38),'Concrete')
    for rect in room['ceilings']:H['slab'](rect,'Ceilings',True)
    box('Shell',(9,3.6,3.65),(10,.18,1.3),'Concrete')
    for x0,y0,x1,y1 in room['dock']['stairs']:
        for i in range(4):
            z=(i+1)*.15;y=y0+i*.3
            box('Dock',((x0+x1)/2,y+.15,z/2),(x1-x0,.3,z),'Concrete')
            box('Dock',((x0+x1)/2,y+.025,z+.003),(x1-x0,.045,.006),'BareSteel')
    for x0,x1 in ((.15,1.9),(5.1,12.9),(16.1,17.85)):
        box('Dock',((x0+x1)/2,13.97,.57),(x1-x0,.085,.09),'BareSteel')
    freight_guardrails(H)
    build_freight_door(H)
    # Short overhead I rail carried on two cross beams, with parked hoist above the dock.
    for z in (3.80,4.0):box('Rigging',(9,14,z),(.24,7.5,.045),'BareSteel')
    box('Rigging',(9,14,3.9),(.025,7.5,.18),'PaintedSteel')
    for y in (10.6,16.5):box('Rigging',(9,y,4.09),(.38,.30,.12),'BareSteel')
    box('Rigging',(9,16.75,3.60),(.36,.47,.30),'ServicePaint')
    for x in (8.83,9.17):
        tube('Rigging',[(x,16.75,3.77),(x+.025,16.75,3.77)],.065,'BareSteel',32)
    for z in (3.29,3.35,3.41):detail.torus((9,16.75,z),(1,0,0),.045,.007,kind='Rigging',mat='BareSteel')
    tube('Rigging',[(9,16.75,3.3),(9,16.75,3.22),(9.055,16.75,3.18),(9.09,16.75,3.21)],.017,'BareSteel')
    pallet(1.35,9.8,0,.07);pallet(1.39,9.76,.215,.02)
    rack(16.75,16,.6)
    build_pallet_jack(H)
    # Floor transport markings belong to the loading bays, never cover the whole room.
    for x in (2.35,15.85):box('Markings',(x,10.7,.003),(.075,3.6,.005),'YellowPaint')
    for x in (5.7,12.3):
        for j in range(4):box('Markings',(x+j*.18,14.35,.604),(.085,.32,.006),'YellowPaint',-.52)

for index,room in enumerate(H['CFG']['rooms']):
    H['ROOM']=room;H['GROUPS']={};H['R']=random.Random(H['CFG']['seed']+index)
    if room['id']=='VentilationLoop':ventilation()
    else:freight()
    for edge,(a,b) in enumerate(zip(room['footprint'],room['footprint'][1:]+room['footprint'][:1])):
        H['wall'](a,b,room['height_m'],[o for o in room['openings'] if o['edge']==edge])
    for x,y in room['columns']:box('Shell',(x,y,room['height_m']/2),(.32,.32,room['height_m']))
    for a,b in room['beams']:bar('Shell',a,b,.32,.32)
    for p in room['pipes']:H['smooth_pipe'](p['points'],p['radius'])
    for l in room['lights']:H['lamp'](l)
    # Model actual ceiling suspension for every fixture.
    for l in room['lights']:
        x,y,z=l['at'];top=detail.ceiling_at(Vector((x,y,z)))
        for dx in (-.34,.34):tube('Fixtures',[(x+dx,y,z+.035),(x+dx,y,top)],.008,'BareSteel',12)
    for a in room['anchors']:H['ANCHORS'].append(dict(room=room['id'],origin_m=room['origin_m'],**a))
    if 'Lift' in H['GROUPS']:
        export_lift(H)
        del H['GROUPS']['Lift']
    H['export']()
    print('ROOM_EXPORTED',room['id'],flush=True)

for record in H['RECORDS']:
    if record['kind'] in ('Fixtures','Markings'):record['collision']=False
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/Dungeon_VentFreight.blend'))
(ROOT/'Authored/manifest.json').write_text(json.dumps(dict(objects=H['RECORDS'],lights=H['LIGHTS'],anchors=H['ANCHORS']),indent=2),encoding='utf-8')
(ROOT/'Authored/surface-provenance.json').write_text(json.dumps(dict(source=str(H['SURFACES'].source),placements=H['SURFACES'].placements,tests_run=False),indent=2),encoding='utf-8')
print('VENT_FREIGHT_AUTHORED',len(H['RECORDS']),flush=True)
