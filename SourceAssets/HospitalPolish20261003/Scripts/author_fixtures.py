"""Original wall-connected pump skid and hospital scrub sink. Author/export only."""
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
library=PROJECT/'SourceAssets/WarehouseContainers20261002/Scripts/author_containers.py'
exec(compile(library.read_text('utf8').split('def wood_crate():')[0],str(library),'exec'))
BASE='/Game/Dungeons/HospitalPolish20261003'
for material in list(bpy.data.materials):bpy.data.materials.remove(material)
MAP=dict(Steel='/Game/Dungeons/StaffLiving20261002/WallInsetV6/Materials/M_Staff_Stainless_V6',
    Rubber='/Game/Dungeons/StaffLiving20261002/WallInsetV6/Materials/M_Staff_KettleRubber_V6',
    Paint='/Game/Dungeons/HospitalContainers20261003/Materials/M_Hospital_Green',
    Red='/Game/Dungeons/HospitalContainers20261003/Materials/M_Hospital_Red',
    Blue='/Game/Dungeons/HospitalContainers20261003/Materials/M_Hospital_Blue',
    White='/Game/Dungeons/HospitalContainers20261003/Materials/M_Hospital_White')
MATS={key:bpy.data.materials.new('RS_'+key) for key in MAP}


def rod(a,b,r=.010,mat='Steel',sides=32):
    a,b=Vector(a),Vector(b)
    return cylinder((a+b)*.5,r,(b-a).length,mat,axis=b-a,sides=sides)


def torus(c,normal,major,minor,mat='Steel'):
    bpy.ops.mesh.primitive_torus_add(major_segments=64,minor_segments=12,location=c,major_radius=major,minor_radius=minor)
    obj=bpy.context.object;obj.rotation_euler=Vector(normal).to_track_quat('Z','Y').to_euler()
    for face in obj.data.polygons:face.use_smooth=True
    return finish(obj,mat,0)


def flange(c,axis,r=.105,pipe=.063):
    n=Vector(axis).normalized();c=Vector(c)
    cylinder(c,r,.022,axis=n,sides=48)
    cylinder(c+n*.013,r*.76,.008,'Rubber',axis=n,sides=48)
    u=n.cross(Vector((0,0,1)) if abs(n.z)<.9 else Vector((0,1,0))).normalized();v=n.cross(u)
    for index in range(6):
        at=c+r*.78*(math.cos(index*math.tau/6)*u+math.sin(index*math.tau/6)*v)
        cylinder(at+n*.014,.009,.014,axis=n,sides=6)
        cylinder(at-n*.014,.012,.005,axis=n,sides=24)


def handwheel(x,y,z):
    # The stem, bonnet and wheel hub form a continuous mechanical connection.
    cylinder((x,y,z-.15),.057,.13,'Paint',sides=48)
    cylinder((x,y,z-.065),.035,.055,axis=(0,0,1),sides=32)
    rod((x,y,z-.05),(x,y,z+.011),.010)
    cylinder((x,y,z),.029,.026,'Steel',sides=32)
    torus((x,y,z),(0,0,1),.137,.011,'Red')
    for angle in (0,math.tau/3,math.tau*2/3):
        rod((x,y,z),(x+.135*math.cos(angle),y+.135*math.sin(angle),z),.007,'Red',24)
    cylinder((x,y,z+.018),.012,.010,axis=(0,0,1),sides=6)


def gauge(x,y,z):
    # Dial faces the working aisle; pressure branch reaches the actual valve body.
    rod((x-.14,y-.02,z),(x,y-.02,z),.009)
    cylinder((x,y,z),.071,.036,axis=(0,1,0),sides=48)
    cylinder((x,y+.021,z),.061,.004,'White',axis=(0,1,0),sides=48)
    torus((x,y+.023,z),(0,1,0),.064,.005)
    for index in range(9):
        t=math.radians(-135+index*33.75)
        rod((x+.044*math.sin(t),y+.025,z+.044*math.cos(t)),
            (x+.053*math.sin(t),y+.025,z+.053*math.cos(t)),.0016,'Rubber',8)
    rod((x,y+.027,z),(x-.031,y+.027,z+.029),.002,'Red',12)
    cylinder((x,y+.029,z),.007,.006,'Steel',axis=(0,1,0),sides=20)


def pump():
    box((0,0,.10),(2.28,1.04,.14),'Steel',.012)
    for x in (-.61,.61):
        for y in (-.34,.34):
            box((x,y,.023),(.27,.22,.046),'Rubber',.009)
            cylinder((x,y,.18),.014,.023,axis=(0,0,1),sides=6)
        box((x,0,.223),(.43,.69,.112),'Paint',.012)
        # Motor barrel, fins, vented fan end, mounting feet and terminal box.
        cylinder((x,.26,.57),.205,.44,'Paint',axis=(0,1,0),sides=64)
        for index in range(13):
            cylinder((x,.10+index*.026,.57),.221,.011,'Paint',axis=(0,1,0),sides=64)
        cylinder((x,.503,.57),.195,.048,'Paint',axis=(0,1,0),sides=64)
        torus((x,.531,.57),(0,1,0),.165,.009,'Steel')
        for angle in range(0,360,30):
            t=math.radians(angle)
            rod((x+.03*math.cos(t),.536,.57+.03*math.sin(t)),(x+.158*math.cos(t),.536,.57+.158*math.sin(t)),.004,'Rubber',12)
        for xx in (x-.13,x+.13):box((xx,.26,.325),(.06,.32,.08),'Paint',.006)
        box((x,.29,.80),(.20,.18,.10),'Paint',.007)
        for dx in (-.071,.071):
            for dy in (-.051,.051):cylinder((x+dx,.29+dy,.855),.006,.008,axis=(0,0,1),sides=6)
        # Guarded shaft/coupler and volute housing have real joined interfaces.
        cylinder((x,-.037,.57),.105,.10,'Steel',axis=(0,1,0),sides=48)
        cylinder((x,-.205,.57),.249,.23,'Paint',axis=(0,1,0),sides=64)
        torus((x,-.326,.57),(0,1,0),.212,.009,'Steel')
        for angle in range(0,360,45):
            t=math.radians(angle);cylinder((x+.207*math.cos(t),-.338,.57+.207*math.sin(t)),.009,.012,axis=(0,1,0),sides=6)
        # Inlet bends into the rear wall, with wall flange and supported pipe.
        tube([(x,-.325,.56),(x,-.39,.56),(x,-.445,.58),(x,-.48,.63),
              (x,-.50,.72),(x,-.52,.81),(x,-.565,.86),(x,-.64,.86)],.062,'Paint')
        flange((x,-.35,.56),(0,1,0));flange((x,-.627,.86),(0,1,0))
        # Outlet stem includes actual gate bonnet under the wheel.
        rod((x,-.205,.78),(x,-.205,1.28),.062,'Paint',48)
        flange((x,-.205,.91),(0,0,1));flange((x,-.205,1.23),(0,0,1))
        cylinder((x,-.205,1.11),.092,.17,'Paint',sides=48)
        handwheel(x,-.205,1.49)
        gauge(x+.14,-.119,1.11)
        tube([(x,-.205,1.28),(x,-.205,1.325),(x,-.235,1.363),
              (x,-.285,1.378),(x,-.40,1.378),(x,-.64,1.378)],.062,'Paint')
        flange((x,-.627,1.378),(0,1,0))
        # Rear pipe saddle reaches its bolted wall bracket.
        for z in (.86,1.378):
            box((x,-.623,z),(.22,.03,.22),'Steel',.006)
            for dx in (-.085,.085):
                for dz in (-.085,.085):cylinder((x+dx,-.603,z+dz),.009,.012,axis=(0,1,0),sides=6)
        tube([(x,.29,.855),(x,.26,.93),(x,.03,.95),(x,-.51,.95),(0,-.51,.98),(0,-.60,1.05)],.009,'Rubber')
    box((0,-.602,1.18),(.30,.07,.36),'Paint',.008)
    box((0,-.558,1.18),(.25,.012,.30),'Rubber',.004)
    for x,mat in ((-.066,'Red'),(.066,'Blue')):
        cylinder((x,-.547,1.16),.018,.021,mat,axis=(0,1,0),sides=32)
    box((0,-.644,1.18),(.34,.013,.40),'Steel',.004)
    hulls=[((0,0,.105),(2.28,1.04,.21)),((0,-.615,1.17),(.35,.06,.41))]
    for x in (-.61,.61):
        hulls.extend([((x,.15,.52),(.52,.84,.72)),((x,-.21,1.19),(.23,.22,.74)),
                      ((x,-.52,.86),(.19,.25,.16)),((x,-.51,1.38),(.19,.29,.16))])
    emit('SM_Hospital_WallPump_V2',hulls=hulls)


def perforated_bottom():
    # A real circular drain in a closed thickness plate; no black disk over a solid bowl.
    cx,cy=.18,.015;inner=.032;count=64;vertices=[]
    for z in (.730,.751):
        for outside in (False,True):
            for index in range(count):
                t=math.tau*index/count;dx,dy=math.cos(t),math.sin(t)
                distance=min(((.48-cx)/dx if dx>0 else (-.48-cx)/dx) if abs(dx)>.0001 else 1e5,
                             ((.295-cy)/dy if dy>0 else (-.295-cy)/dy) if abs(dy)>.0001 else 1e5) if outside else inner
                vertices.append((cx+distance*dx,cy+distance*dy,z))
    faces=[]
    for index in range(count):
        nxt=(index+1)%count
        faces.extend([(index,nxt,nxt+count,index+count),
            (index+2*count,index+3*count,nxt+3*count,nxt+2*count),
            (index,index+2*count,nxt+2*count,nxt),
            (index+count,nxt+count,nxt+3*count,index+3*count)])
    mesh=bpy.data.meshes.new('Sink formed floor with drain');mesh.from_pydata(vertices,[],faces);mesh.update()
    obj=bpy.data.objects.new('Sink formed floor with drain',mesh);bpy.context.scene.collection.objects.link(obj);finish(obj,'Steel',0)


def sink():
    for x in (-.45,.45):
        for y in (-.27,.27):
            box((x,y,.43),(.045,.045,.84),'Steel',.005)
            box((x,y,.012),(.065,.065,.024),'Rubber',.004)
    for x in (-.45,.45):rod((x,-.27,.28),(x,.27,.28),.012)
    rod((-.45,-.27,.28),(.45,-.27,.28),.012)
    perforated_bottom()
    for x in (-.496,.496):box((x,0,.839),(.032,.64,.208),'Steel',.010)
    for y in (-.307,.307):box((0,y,.839),(1.024,.032,.208),'Steel',.010)
    tube([(-.514,.323,.944),(.514,.323,.944),(.514,-.323,.944),(-.514,-.323,.944),(-.514,.323,.944)],.014)
    # Wide rear deck meets the splashback at its bottom seam.
    box((0,-.297,.951),(1.056,.112,.035),'Steel',.007)
    box((0,-.357,1.151),(1.056,.026,.37),'Steel',.006)
    rod((-.52,-.338,.976),(.52,-.338,.976),.010)
    # Splashback uses wall pads with its rear installation face exactly at +37 cm UE Y.
    for x in (-.38,.38):
        for z in (1.035,1.27):
            box((x,-.369,z),(.07,.005,.055),'Rubber',.001)
            cylinder((x,-.339,z),.007,.010,axis=(0,1,0),sides=6)
    # Goose-neck faucet, aerator and hot/cold handles all connect to the rear deck.
    tube([(0,-.271,.969),(0,-.271,1.185),(0,-.264,1.246),(0,-.239,1.285),
          (0,-.194,1.306),(0,-.11,1.306),(0,-.036,1.29),(0,.02,1.256),(0,.043,1.208)],.018)
    cylinder((0,-.271,.983),.035,.026)
    cylinder((0,.043,1.197),.023,.035)
    torus((0,.043,1.18),(0,0,1),.019,.003)
    for x,mat in ((-.155,'Red'),(.155,'Blue')):
        cylinder((x,-.271,.989),.026,.055)
        cylinder((x,-.271,1.03),.019,.018,mat)
        rod((x-.041,-.271,1.027),(x+.041,-.271,1.027),.006)
        tube([(x,-.271,.966),(x,-.271,.653),(x,-.31,.635),(x,-.37,.635)],.011)
        flange((x,-.356,.635),(0,1,0),.032,.011)
    # Drain ring, removable grate and continuous P-trap into the wall escutcheon.
    torus((.18,.015,.755),(0,0,1),.034,.004)
    for dx in (-.018,-.006,.006,.018):
        dy=math.sqrt(.028**2-dx**2);rod((.18+dx,.015-dy,.749),(.18+dx,.015+dy,.749),.0016,'Steel',8)
    cylinder((.18,.015,.711),.038,.038)
    tube([(.18,.015,.710),(.18,.015,.468),(.18,.010,.439),(.18,-.008,.410),
          (.18,-.039,.391),(.18,-.083,.384),(.18,-.129,.395),(.18,-.166,.426),
          (.18,-.184,.470),(.18,-.184,.526),(.18,-.196,.553),(.18,-.225,.568),(.18,-.37,.568)],.028)
    flange((.18,-.358,.568),(0,1,0),.065,.028)
    for z in (.670,.500):
        cylinder((.18,.015,z),.035,.030)
    hulls=[((0,0,.742),(.965,.59,.025)),((-.496,0,.839),(.032,.64,.208)),
           ((.496,0,.839),(.032,.64,.208)),((0,-.307,.839),(1.024,.032,.208)),
           ((0,.307,.839),(1.024,.032,.208)),((0,-.357,1.151),(1.056,.026,.37))]
    for x in (-.45,.45):
        for y in (-.27,.27):hulls.append(((x,y,.43),(.045,.045,.86)))
    emit('SM_Hospital_ScrubSink_V2',hulls=hulls)


pump();sink()
for obj in bpy.data.objects:obj.hide_set(False)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'HospitalFixtures_Source.blend'))
(OUT/'manifest.json').write_text(json.dumps(dict(objects=records,provenance='Original Blender geometry, existing project materials',
    rear_interfaces_cm=dict(Pump=[0,64,0],Sink=[0,37,0]),tests_run=False,rendered=False),ensure_ascii=False,indent=2),encoding='utf8')
print('HOSPITAL_WALL_FIXTURES_AUTHORED '+str(len(records)),flush=True)
