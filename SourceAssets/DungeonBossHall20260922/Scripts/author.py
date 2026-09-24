"""Model the authored two-storey terminal hall without opening Unreal or rendering."""
import os,json,math,random,sys
from pathlib import Path
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Scripts'))
LIB=ROOT.parent/'DungeonRoomShells20260922/Scripts/author_rooms.py'
os.environ['DUNGEON_AUTHOR_ROOT']=str(ROOT)
source=LIB.read_text(encoding='utf-8').split("for index,room in enumerate(CFG['rooms']):",1)[0]
H={'__file__':str(LIB),'__name__':'boss_architecture_library'}
exec(compile(source,str(LIB),'exec'),H)
box,poly,tube,bar,detail=(H[k] for k in ('box','poly','tube','bar','detail'))
for key,path in dict(Rubber='/Game/Dungeons/AtmosphereV2/RoomInteriors/Materials/M_Room_Rubber',YellowPaint='/Game/Dungeons/AtmosphereV2/RoomInteriors/Materials/M_Room_YellowPaint').items():
    H['MAPPING'][key]=path;H['MATS'][key]=bpy.data.materials.new('RS_'+key)
for key in ('BossMachinePaint','BossStructuralSteel','BossGrating','BossFloor','BossFoundation','BossWetConcrete','BossGauge','BossLabel','BossCableJacket','BossPipeCoat','BossPipeHardware'):
    H['MAPPING'][key]='/Game/Dungeons/BossHall20260922/Materials/M_'+key
    H['MATS'][key]=bpy.data.materials.new('RS_'+key)
room=H['CFG']['rooms'][0];H['ROOM']=room;H['GROUPS']={};H['R']=random.Random(H['CFG']['seed'])
from service_routing import install,construct
install(H)

def oriented_box(kind,center,axes,size,mat):
    c=Vector(center);u,v,w=axes;a,b,d=[s/2 for s in size]
    vs=[tuple(c+u*x+v*y+w*z) for x,y,z in [(-a,-b,-d),(a,-b,-d),(a,b,-d),(-a,b,-d),(-a,-b,d),(a,-b,d),(a,b,d),(-a,b,d)]]
    poly(kind,vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)

def ibeam(kind,a,b,width=.22,height=.32,thick=.016,mat='BossStructuralSteel'):
    a,b=Vector(a),Vector(b);d=b-a;axis=d.normalized()
    helper=Vector((0,0,1)) if abs(axis.z)<.9 else Vector((0,1,0))
    side=helper.cross(axis).normalized();up=axis.cross(side).normalized();axes=(side,up,axis);center=(a+b)/2
    for sign in (-1,1):oriented_box(kind,center+up*sign*(height-thick)/2,axes,(width,thick,d.length),mat)
    oriented_box(kind,center,axes,(thick,height-2*thick,d.length),mat)

from guardrails import Guardrails
GUARDS=Guardrails(H,oriented_box)

def rail(a,b,base=3.6,kind='GalleryRails',yellow=True):
    GUARDS.horizontal(a,b,base,kind,yellow)

def grate_deck(rect,z,kind='GalleryDeck'):
    x0,y0,x1,y1=rect
    # Lift-out panels with real gaps; no 22 m unsupported bearing flats at the rear.
    nx=max(1,math.ceil((x1-x0)/1.12));ny=max(1,math.ceil((y1-y0)/1.20))
    for ix in range(nx):
        for iy in range(ny):
            a=x0+(x1-x0)*ix/nx+.006;b=x0+(x1-x0)*(ix+1)/nx-.006
            c=y0+(y1-y0)*iy/ny+.006;d=y0+(y1-y0)*(iy+1)/ny-.006
            for y in (c+.012,d-.012):box(kind,((a+b)/2,y,z-.026),(b-a,.024,.052),'BossGrating')
            for x in (a+.012,b-.012):box(kind,(x,(c+d)/2,z-.026),(.024,d-c,.052),'BossGrating')
            n=max(2,math.ceil((d-c-.07)/.045))
            for i in range(n+1):
                y=c+.035+(d-c-.07)*i/n
                box(kind,((a+b)/2,y,z-.022),(b-a-.048,.006,.044),'BossGrating')
            for i in range(1,5):box(kind,(a+(b-a)*i/5,(c+d)/2,z-.032),(.007,d-c-.048,.018),'BossGrating')
            if kind=='GalleryDeck':
                for x,y in ((a+.06,c+.06),(b-.06,d-.06)):
                    box(kind,(x,y,z+.004),(.075,.025,.008),'BareSteel')
    # Intermediate panel ledgers join transverse platform beams.
    for ix in range(1,nx):
        x=x0+(x1-x0)*ix/nx
        box(kind,(x,(y0+y1)/2,z-.078),(.045,y1-y0,.05),'BossStructuralSteel')

def platform(spec):
    x0,y0,x1,y1=spec['rect'];z=room['platform_height_m']
    grate_deck(spec['rect'],z)
    for x in (x0+.10,x1-.10):ibeam('GalleryFrames',(x,y0,z-.21),(x,y1,z-.21),.22,.32)
    n=max(1,math.ceil((y1-y0)/2.4))
    for i in range(n+1):
        y=y0+(y1-y0)*i/n
        ibeam('GalleryFrames',(x0,y,z-.23),(x1,y,z-.23),.18,.26)
    # Bolted corner seats beneath the grating frames.
    for x in (x0+.13,x1-.13):
        for y in (y0+.12,y1-.12):
            box('GalleryFrames',(x,y,z-.067),(.2,.2,.035),'BareSteel')
            detail.fastener((x,y,z-.045),(0,0,1),.013,kind='GalleryFrames')

def flight(x0,x1,y0,z0,count,rise,run,kind):
    for i in range(count):
        y=y0+i*run;z=z0+(i+1)*rise
        grate_deck([x0,y,x1,y+run],z,kind)
        box(kind,((x0+x1)/2,y+.026,z+.003),(x1-x0,.052,.006),'YellowPaint')
        for x in (x0+.04,x1-.04):detail.fastener((x,y+.19,z+.008),(0,0,1),.009,kind=kind)
    end_y=y0+count*run;end_z=z0+count*rise
    for x in (x0+.035,x1-.035):
        ibeam(kind,(x,y0,z0-.06),(x,end_y,end_z-.21),.10,.25,.012)
    return end_y,end_z

def staircase(s):
    x0,x1,y0=s['x0'],s['x1'],s['y0'];kind='Stair'+s['id']
    y,z=flight(x0,x1,y0,0,s['steps_per_flight'],s['rise'],s['run'],kind)
    grate_deck([x0,y,x1,y+s['landing']],z,kind)
    for x in (x0+.06,x1-.06):
        ibeam(kind,(x,y,z-.18),(x,y+s['landing'],z-.18),.14,.25)
        for yy in (y+.10,y+s['landing']-.10):ibeam(kind,(x,yy,.08),(x,yy,z-.23),.14,.16)
    flight(x0,x1,y+s['landing'],z,s['steps_per_flight'],s['rise'],s['run'],kind)
    GUARDS.staircase(s,kind)
    for x in (x0+.04,x1-.04):
        box(kind,(x,y0,.03),(.28,.35,.06),'BareSteel')
        for yy in (y0-.10,y0+.10):detail.fastener((x,yy,.068),(0,0,1),.015,kind=kind)

def motor_fins(center,radius,length,kind):
    x,y,z=center
    tube(kind,[(x,y-length/2+.13,z),(x,y+length/2,z)],radius,'BossMachinePaint',64)
    for i in range(28):
        a=math.tau*i/28
        axis=Vector((math.cos(a),0,math.sin(a)));tangent=Vector((math.sin(a),0,-math.cos(a)))
        oriented_box(kind,Vector(center)+axis*(radius+.027),(axis,tangent,Vector((0,1,0))),(.072,.021,length*.72),'BossMachinePaint')
    for yy in (y-length/2+.04,y+length/2-.04):detail.ring((x,yy,z),(0,1,0),radius+.035,radius-.025,.065,'BareSteel',64,kind)
    for dx in (-radius*.62,radius*.62):
        box(kind,(x+dx,y,.835),(.20,length*.74,.25),'BossStructuralSteel')
    # Recessed fan behind open grille and annular shroud, not bars laid on a solid cap.
    front=y-length/2-.12
    detail.ring((x,front+.12,z),(0,1,0),radius+.035,radius-.035,.26,'BossMachinePaint',64,kind)
    tube(kind,[(x,front+.21,z),(x,front+.23,z)],radius*.89,'Rubber',64)
    detail.ring((x,front,z),(0,1,0),radius+.038,radius-.027,.035,'BossStructuralSteel',64,kind)
    for i in range(-9,10):
        xx=i*radius/10;h=math.sqrt(max(0,(radius*.91)**2-xx*xx))
        if h>.01:box(kind,(x+xx,front,z),(.010,.014,h*2),'BossStructuralSteel')
    for i in range(-4,5):
        zz=i*radius/5;w=math.sqrt(max(0,(radius*.91)**2-zz*zz))
        if w>.01:box(kind,(x,front+.019,z+zz),(w*2,.012,.008),'BareSteel')
    box(kind,(x+.10,y,z+radius+.16),(.54,.48,.27),'BossMachinePaint')
    box(kind,(x+.10,y,z+radius+.305),(.58,.52,.03),'BossStructuralSteel')
    for xx in (x-.12,x+.32):
        for yy in (y-.19,y+.19):detail.fastener((xx,yy,z+radius+.325),(0,0,1),.01,kind)
    # Cable gland faces the adjacent control pedestal, keeping the lead off the cooling fins.
    tube(kind,[(x-.17,y,z+radius+.12),(x-.30,y,z+radius+.12)],.040,'BossCableJacket',24)

def revolved(kind,center,axis,profile,mat,sides=64):
    """Lathe a closed profile: each pair is (axial distance, radius)."""
    c=Vector(center);n=Vector(axis).normalized();u=n.cross(Vector((0,0,1)) if abs(n.z)<.9 else Vector((0,1,0))).normalized();v=n.cross(u)
    vs=[tuple(c+n*t+r*(u*math.cos(j*math.tau/sides)+v*math.sin(j*math.tau/sides))) for t,r in profile for j in range(sides)]
    fs=[];uv=[];smooth=[]
    for i in range(len(profile)-1):
        for j in range(sides):
            fs.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j))
            uv.append([(j/sides*4,profile[i][0]/.8),((j+1)/sides*4,profile[i][0]/.8),((j+1)/sides*4,profile[i+1][0]/.8),(j/sides*4,profile[i+1][0]/.8)])
            smooth.append(True)
    for index in (0,len(profile)-1):
        ids=list(range(index*sides,(index+1)*sides))
        if index==0:ids.reverse()
        fs.append(ids);uv.append([(Vector(vs[i]).dot(u),Vector(vs[i]).dot(v)) for i in ids]);smooth.append(False)
    poly(kind,vs,fs,mat,uv,smooth)

def face_plate(kind,center,width,height,mat):
    x,y,z=center
    poly(kind,[(x-width/2,y,z-height/2),(x+width/2,y,z-height/2),(x+width/2,y,z+height/2),(x-width/2,y,z+height/2)],[(0,1,2,3)],mat,[[[0,0],[1,0],[1,1],[0,1]]])

def gauge(kind,center):
    x,y,z=center
    tube(kind,[(x,y+.018,z),(x,y-.008,z)],.099,'BossStructuralSteel',48)
    detail.ring((x,y-.018,z),(0,-1,0),.103,.090,.032,'BareSteel',48,kind)
    # Circular face with planar atlas coordinates and a separate physical needle.
    vs=[(x+.089*math.cos(a*math.tau/64),y-.036,z+.089*math.sin(a*math.tau/64)) for a in range(64)]
    poly(kind,vs,[tuple(range(64))],'BossGauge',[[((p[0]-x)/.178+.5,(p[2]-z)/.178+.5) for p in vs]])
    tube(kind,[(x-.012,y-.042,z-.010),(x+.052,y-.042,z+.042)],.0024,'BareSteel',12)
    tube(kind,[(x,y-.043,z),(x,y-.048,z)],.007,'BareSteel',16)

def wheel(center,axis,kind):
    c,n=Vector(center),Vector(axis).normalized();side=n.cross(Vector((0,0,1))).normalized();up=n.cross(side)
    detail.torus(c,n,.28,.022,kind,'YellowPaint',48)
    tube(kind,[c-n*.19,c+n*.035],.034,'BareSteel',24)
    for i in range(5):
        a=i*math.tau/5;tube(kind,[c,c+(side*math.cos(a)+up*math.sin(a))*.26],.014,'YellowPaint',12)

def machine(m):
    x,y,z=m['at'];w,d,h=m['base'];kind=m['id']
    box('MachineBases',(x,y,h/2),(w,d,h),'BossFoundation')
    for xx in (x-1.25,x+1.25):
        ibeam(kind,(xx,y-1.95,h+.11),(xx,y+1.85,h+.11),.24,.20)
        for yy in (y-1.8,y+1.7):detail.fastener((xx,yy,h+.23),(0,0,1),.023,kind=kind)
    # Transverse bed members physically carry motor feet and pump feet onto both skids.
    for yy in (y-1.52,y-.50,y+.45,y+1.00):
        ibeam(kind,(x-1.36,yy,.675),(x+1.36,yy,.675),.22,.09,.012)
    motor_fins((x,y-1.00,1.43),.60,1.64,kind)
    for xx in (x-.37,x+.37):
        for yy in (y-1.49,y-.51):detail.fastener((xx,yy,.973),(0,0,1),.020,kind)
    # Rounded cast casing shoulders, gasket seam and removable rear cover.
    revolved(kind,(x,y,1.43),(0,1,0),[(.27,.40),(.34,.68),(.43,.85),(.54,.91),(.76,.93),(.97,.87),(1.10,.68),(1.15,.37)],'BossMachinePaint',80)
    detail.ring((x,y+.48,1.43),(0,1,0),.958,.80,.075,'BossMachinePaint',80,kind)
    detail.ring((x,y+.532,1.43),(0,1,0),.949,.88,.014,'Rubber',80,kind)
    detail.ring((x,y+.56,1.43),(0,1,0),.953,.80,.045,'BossMachinePaint',80,kind)
    tube(kind,[(x,y-.20,1.43),(x,y+.34,1.43)],.14,'BareSteel',32)
    detail.ring((x,y+.04,1.43),(0,1,0),.25,.135,.13,'BossMachinePaint',48,kind)
    for i in range(16):
        a=i*math.tau/16
        detail.fastener((x+.895*math.cos(a),y+.436,1.43+.895*math.sin(a)),(0,-1,0),.023,kind=kind)
    for xx in (x-.63,x+.63):
        box(kind,(xx,y+.70,.865),(.24,.84,.30),'BossMachinePaint')
        box(kind,(xx,y+.70,.737),(.36,.91,.05),'BossStructuralSteel')
        for yy in (y+.36,y+1.04):detail.fastener((xx,yy,.772),(0,0,1),.020,kind)
    # Axial suction elbow and a connected discharge neck distinguish the pump from its motor.
    tube(kind,[(x,y+1.11,1.43),(x,y+1.53,1.43)],.31,'BossMachinePaint',48)
    detail.ring((x,y+1.49,1.43),(0,1,0),.39,.29,.09,'BossMachinePaint',48,kind)
    H['smooth_pipe']([(x,y+1.48,1.43),(x,y+2.02,1.43),(x,y+2.02,.39)],.285)
    # Perforated coupling guard: multiple arc ribs and longitudinal slats leave real openings.
    for yy in (y-.10,y+.19):
        pts=[(x+.31*math.cos(i*math.pi/20),yy,1.43+.31*math.sin(i*math.pi/20)) for i in range(21)]
        tube(kind,pts,.013,'YellowPaint',12)
    for i in range(11):
        a=i*math.pi/10
        tube(kind,[(x+.31*math.cos(a),y-.11,1.43+.31*math.sin(a)),(x+.31*math.cos(a),y+.20,1.43+.31*math.sin(a))],.009,'YellowPaint',12)
    # Large pipe exits above the pump, rises clear of the arena and returns along the side wall.
    side=m['pipe_side'];px=x+.48;py=y+.74
    tube(kind,[(px,py,1.91),(px,py,2.42)],.31,'BossMachinePaint',48)
    detail.ring((px,py,2.35),(0,0,1),.39,.26,.09,'BossMachinePaint',48,kind)
    for i in range(8):
        a=(i+.5)*math.tau/8;detail.fastener((px+.34*math.cos(a),py+.34*math.sin(a),2.401),(0,0,1),.018,kind)
    H['smooth_pipe']([(px,py,2.39),(px,py,6.35),(side*14.15,py,6.35),(side*14.15,26.24,6.35)],.27)
    detail.ring((side*14.15,25.90,6.35),(0,1,0),.44,.275,.10,'BossStructuralSteel',48,'WallServices')
    wheel((px+side*.56,py,2.70),(side,0,0),kind)
    tube(kind,[(px,py,2.70),(px+side*.55,py,2.70)],.044,'BareSteel')
    # Small attached panel and gauge are mounted to the machine frame.
    box(kind,(x-1.48,y-.45,1.12),(.28,.52,.70),'BossMachinePaint')
    box(kind,(x-1.48,y-.45,.61),(.13,.18,.36),'BossStructuralSteel')
    gauge(kind,(x-1.48,y-.73,1.25))
    face_plate(kind,(x-1.48,y-.716,.99),.20,.11,'BossLabel')
    for xx in (x-1.56,x-1.40):
        detail.fastener((xx,y-.72,1.44),(0,-1,0),.008,kind)
    for xx,mat in ((x-1.54,'YellowPaint'),(x-1.42,'Rubber')):
        tube(kind,[(xx,y-.713,1.08),(xx,y-.733,1.08)],.017,mat,20)

# Floor, high walls and roof keep the same physical material scale as the ordinary rooms.
for rect in room['floors']:H['slab'](rect,'Floors')
# Subdivide only the visible slab face so grime can follow foundations and wall feet.
fg=H['GROUPS']['Floors']
keep=[i for i,f in enumerate(fg['f']) if not all(abs(fg['v'][v][2])<.0001 for v in f)]
for attr in ('f','m','uv','smooth'):fg[attr]=[fg[attr][i] for i in keep]
fg['m']=['BossFloor']*len(fg['m'])
nx,ny=60,52
vs=[(-15+i*.5,j*.5,0) for j in range(ny+1) for i in range(nx+1)]
fs=[(j*(nx+1)+i,j*(nx+1)+i+1,(j+1)*(nx+1)+i+1,(j+1)*(nx+1)+i) for j in range(ny) for i in range(nx)]
poly('Floors',vs,fs,'BossFloor')
# Sparse expansion joints and worn service bay markings, kept flush with walking floor.
for x in (-12,-6,0,6,12):box('FloorDetails',(x,13,.0015),(.008,25.6,.003),'Rubber')
for y in (5,10,15,20,25):box('FloorDetails',(0,y,.0015),(29.4,.008,.003),'Rubber')
for m in room['machines']:
    x,y,_=m['at']
    for xx in (x-2.57,x+2.57):
        for j in range(9):box('FloorDetails',(xx,y-2.5+j*.61,.003),(.065,.39,.004),'YellowPaint')
    for yy in (y-2.76,y+2.76):
        for j in range(8):box('FloorDetails',(x-2.27+j*.64,yy,.003),(.40,.065,.004),'YellowPaint')
    # Local damp footprint beside seal/discharge, irregular outline rather than a room-wide gloss.
    for index,(dx,dy,sx,sy) in enumerate(((1.9,.55,1.2,1.7),(-1.15,2.3,1.0,.8))):
        vs=[]
        for j in range(48):
            a=j*math.tau/48;r=1+.14*math.sin(5*a+index)+.10*math.cos(9*a+x)
            vs.append((x+dx+math.cos(a)*sx*r,y+dy+math.sin(a)*sy*r,.004+index*.001))
        inner=[(x+dx+(p[0]-x-dx)*.80,y+dy+(p[1]-y-dy)*.80,p[2]) for p in vs]
        # The same XY UV as floor beneath; no doubled grain or hard decal boundary.
        poly('FloorDetails',vs+inner,[(i,(i+1)%48,48+(i+1)%48,48+i) for i in range(48)]+[tuple(range(48,96))],'BossWetConcrete')
for rect in room['ceilings']:H['slab'](rect,'Ceilings',True)
for edge,(a,b) in enumerate(zip(room['footprint'],room['footprint'][1:]+room['footprint'][:1])):
    H['wall'](a,b,room['height_m'],[o for o in room['openings'] if o['edge']==edge])
for x,y in room['columns']:
    box('Columns',(x,y,3.6),(.55,.65,7.2),'Concrete')
    box('Columns',(x,y,.18),(.78,.88,.36),'Concrete')
    box('Columns',(x,y,3.31),(.74,.86,.16),'BareSteel')
    for yy in (y-.29,y+.29):detail.fastener((x-.40,yy,3.31),(-1,0,0),.020,kind='Columns')
for y in (5.6,14.6,23):
    ibeam('RoofTrusses',(-14.7,y,7.05),(14.7,y,7.05),.22,.26)
    ibeam('RoofTrusses',(-14.7,y,8.03),(14.7,y,8.03),.22,.26)
    for i in range(10):
        x=-14.7+i*2.94
        ibeam('RoofTrusses',(x,y,7.05),(x+2.94,y,8.03),.09,.10,.009)
        ibeam('RoofTrusses',(x,y,8.03),(x+2.94,y,7.05),.09,.10,.009)
    for x in (-11.32,11.32):box('RoofTrusses',(x,y,7.02),(.78,.70,.14),'BareSteel')
for spec in room['platforms']:platform(spec)
for x in (-7.4,0,7.4):
    for y in (22.2,25.3):
        ibeam('GalleryFrames',(x,y,.06),(x,y,3.24),.20,.24)
        box('GalleryFrames',(x,y,.03),(.42,.42,.06),'BareSteel')
        for dx in (-.14,.14):
            for dy in (-.14,.14):detail.fastener((x+dx,y+dy,.067),(0,0,1),.017,kind='GalleryFrames')
for y in (22.2,25.3):ibeam('GalleryFrames',(-11.15,y,3.30),(11.15,y,3.30),.24,.40)
for x,y in ((-7.85,12.65),(7.85,14.45)):
    ibeam('GalleryFrames',(x,y,.06),(x,y,3.24),.18,.22)
    box('GalleryFrames',(x,y,.03),(.36,.36,.06),'BareSteel')
# Kicker brackets under the wall galleries have real columns/wall seats at both ends.
for sign in (-1,1):
    for y in (5.9,14.6,23):
        ibeam('GalleryFrames',(sign*14.65,y,2.10),(sign*11.25,y,3.28),.12,.16)
        box('GalleryFrames',(sign*14.70,y,2.12),(.10,.45,.50),'BareSteel')
for s in room['stairs']:staircase(s)
for a,b in [((-11.15,5.6),(-11.15,11)),((-11.15,12.8),(-11.15,22)),((11.15,5.6),(11.15,12.8)),((11.15,14.6),(11.15,22)),((-11.15,22),(11.15,22)),((-14.65,5.6),(-11.15,5.6)),((11.15,5.6),(14.65,5.6)),((-11.15,12.8),(-7.665,12.8)),((-7.665,11),(-7.665,12.8)),((-11.15,11),(-10.535,11)),((7.665,14.6),(11.15,14.6)),((7.665,12.8),(7.665,14.6)),((10.535,12.8),(11.15,12.8))]:rail(a,b)
for m in room['machines']:machine(m)
# A rear pressure vessel adds a third, narrow equipment silhouette without closing the centre.
revolved('Receiver',(7.5,19.4,0),(0,0,1),[(.57,.08),(.59,.24),(.67,.45),(.79,.58),(.94,.63),(2.65,.63),(2.80,.58),(2.92,.45),(3.00,.24),(3.02,.08)],'BossMachinePaint',64)
for z in (.95,2.65):detail.torus((7.5,19.4,z),(0,0,1),.632,.008,'Receiver','BossStructuralSteel',64)
for a in (0,math.tau/3,2*math.tau/3):
    x=7.5+.48*math.cos(a);y=19.4+.48*math.sin(a)
    ibeam('Receiver',(x,y,.02),(x,y,.83),.12,.14)
    box('Receiver',(x,y,.035),(.24,.24,.07),'BossStructuralSteel')
    detail.fastener((x,y,.079),(0,0,1),.015,'Receiver')
tube('Receiver',[(7.5,19.4,3),(7.5,19.4,3.30)],.065,'BareSteel',32)
detail.ring((7.5,19.4,3.14),(0,0,1),.115,.056,.045,'BossMachinePaint',32,'Receiver')
gauge('Receiver',(7.5,18.73,2.13))
tube('Receiver',[(7.5,18.91,2.13),(7.5,18.77,2.13)],.025,'BareSteel',24)
face_plate('Receiver',(7.5,18.763,1.5),.30,.165,'BossLabel')
# Wall electrical services, trays and small branch conduits reinforce the utility setting.
for sign in (-1,1):
    x=sign*14.5
    for y in (9.5,18.3):
        box('WallServices',(x,y,4.70),(.34,1.08,1.75),'ServicePaint')
        box('WallServices',(x-sign*.185,y,4.70),(.035,.98,1.63),'PaintedSteel')
        tube('WallServices',[(x-sign*.22,y+.32,4.58),(x-sign*.29,y+.32,4.58),(x-sign*.29,y+.32,4.87),(x-sign*.22,y+.32,4.87)],.015,'BareSteel')
construct(H,ibeam)
# Segmented perimeter drain cassettes stay away from the entry and stair mouths.
for x in (-14.8,14.8):
    for y in range(2,25):
        box('Drainage',(x,y,-.012),(.22,.94,.025),'Rubber')
        for j in range(10):box('Drainage',(x,y-.43+j*.095,.006),(.21,.012,.012),'BareSteel')
for l in room['lights']:
    H['lamp'](l);x,y,z=l['at']
    # Fixtures below the gallery are attached to its structure, not through the upper floor.
    support=3.40 if z<3 and abs(x)>11 else 3.45 if y<2 else 8.35
    for dx in (-.34,.34):tube('Fixtures',[(x+dx,y,z+.035),(x+dx,y,support)],.008,'BareSteel',12)
    if y<2:
        for dx in (-.34,.34):ibeam('Fixtures',(x+dx,.08,support),(x+dx,y+.08,support),.05,.07,.008,'BareSteel')
for a in room['anchors']:H['ANCHORS'].append(dict(room=room['id'],origin_m=room['origin_m'],**a))
from export_boss import export
export(H)
for item in H['RECORDS']:
    if item['kind'] in ('Fixtures','CableRoutes','CableTrays','Drainage','FloorDetails'):item['collision']=False
from lookdev import bind
bind()
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/Dungeon_BossPumpHall.blend'))
(ROOT/'Authored/manifest.json').write_text(json.dumps(dict(objects=H['RECORDS'],lights=H['LIGHTS'],anchors=H['ANCHORS']),indent=2),encoding='utf-8')
(ROOT/'Authored/surface-provenance.json').write_text(json.dumps(dict(source=str(H['SURFACES'].source),placements=H['SURFACES'].placements,reference=str(ROOT.parent/'DungeonConcept20260920/V1/02_pump-hall.png'),tests_run=False),indent=2),encoding='utf-8')
(ROOT/'Authored/cable-layout.json').write_text(json.dumps(H['CABLE_LAYOUT'],indent=2),encoding='utf-8')
print('BOSS_HALL_AUTHORED',len(H['RECORDS']),'mesh groups',flush=True)
