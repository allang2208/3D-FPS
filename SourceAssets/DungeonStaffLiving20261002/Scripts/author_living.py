"""Precise staff-living geometry. Background Blender only; no render or test.

Uses the accepted corridor ceramic author, surface scale and industrial materials.
Furniture is reusable; each complete room keeps its own local coordinates.
"""
from pathlib import Path
import json,sys
SCRIPT = Path(__file__).resolve().parent
sys.path.insert(0,str(SCRIPT))
PROJECT = SCRIPT.parents[2]
if not globals().get('_STAFF_REFINEMENT_HELPERS',False):
    author_config=json.loads((SCRIPT.parent/'Config/room.json').read_text('utf8'))
    if author_config.get('coffee_polish_revision',0)>=7:
        author_entry=SCRIPT/'author_coffee_polish_v7.py'
        exec(compile(author_entry.read_text('utf8'),str(author_entry),'exec'))
        raise SystemExit(0)
    if author_config.get('wall_inset_revision',0)>=6:
        author_entry=SCRIPT/'author_wall_inset_v6.py'
        exec(compile(author_entry.read_text('utf8'),str(author_entry),'exec'))
        raise SystemExit(0)
    if author_config.get('room_details_revision',0)>=5:
        author_entry=SCRIPT/'author_room_details_v5.py'
        exec(compile(author_entry.read_text('utf8'),str(author_entry),'exec'))
        raise SystemExit(0)
    if author_config.get('scene_polish_revision',0)>=4:
        author_entry=SCRIPT/'author_scene_polish_v4.py'
        exec(compile(author_entry.read_text('utf8'),str(author_entry),'exec'))
        raise SystemExit(0)
    if author_config.get('container_open_parts_revision',0)>=3:
        author_entry=SCRIPT/'author_container_open_parts_v3.py'
        exec(compile(author_entry.read_text('utf8'),str(author_entry),'exec'))
        raise SystemExit(0)
    if author_config.get('dormitory_layout_revision',0)>=2:
        author_entry=SCRIPT/'author_dormitory_variants_v2.py'
        exec(compile(author_entry.read_text('utf8'),str(author_entry),'exec'))
        raise SystemExit(0)
    if author_config.get('container_interaction_revision',0)>=1:
        author_entry=SCRIPT/'author_search_containers_v1.py'
        exec(compile(author_entry.read_text('utf8'),str(author_entry),'exec'))
        raise SystemExit(0)
    if author_config.get('layout_revision',0)>=3:
        author_entry=SCRIPT/('author_intact_tiles_v4.py' if author_config.get('layout_revision',0)>=4 else 'author_refinement_v3.py')
        exec(compile(author_entry.read_text('utf8'),str(author_entry),'exec'))
        raise SystemExit(0)
exec(compile((PROJECT/'SourceAssets/DungeonAnatomyTheatre20261001/Scripts/geometry.py').read_text('utf-8'),
             'accepted_dungeon_geometry', 'exec'))
detail.setup(globals())
if CFG.get('wall_finish')=='intact':
    from staff_intact_tiles import IntactStaffTiles
    SURFACES=IntactStaffTiles(SURFACES)
OUT.mkdir(parents=True, exist_ok=True)
ATLAS=json.loads((OUT/'atlas.json').read_text('utf-8'))
for key in ('Fabric','SofaFabric','Felt','Ceramic','Linoleum','Mirror','Screen','LampGlass','Labels','OlivePaint'):
    MAPPING[key]=CFG['ue_base']+'/Materials/M_Staff_'+key
    MATS[key]=bpy.data.materials.new('RS_'+key)
MAPPING['Wood']='/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkbenchKit/Materials/Abandoned/MI_WBK_WSBench_BenchWood_R3'
MATS['Wood']=bpy.data.materials.new('RS_Wood')
records=[]
HULLS=[]
SERIAL=0

def collider(c, size, yaw=0):
    HULLS.append((list(c),list(size),yaw))

def chair_leg(a,b,width=.033,mat='PaintedSteel'):
    beam('Body',a,b,width,width,mat)

def cylinder(c,axis,r,length,mat='BareSteel',kind='Body',sides=32):
    detail.tube(kind,[Vector(c)-Vector(axis)*length/2,Vector(c)+Vector(axis)*length/2],r,mat,sides)

def ball(c,r,mat='Ceramic',kind='Body',segments=20,rings=10):
    vs=[(c[0],c[1],c[2]+r)];fs=[]
    for row in range(1,rings):
        t=math.pi*row/rings
        for i in range(segments):
            a=math.tau*i/segments;vs.append((c[0]+r*math.sin(t)*math.cos(a),c[1]+r*math.sin(t)*math.sin(a),c[2]+r*math.cos(t)))
    bottom=len(vs);vs.append((c[0],c[1],c[2]-r))
    for i in range(segments):
        j=(i+1)%segments;fs.append((0,1+i,1+j))
        for row in range(rings-2):
            a=1+row*segments+i;b=1+row*segments+j
            fs.append((a,a+segments,b+segments,b))
        fs.append((bottom,1+(rings-2)*segments+j,1+(rings-2)*segments+i))
    poly(kind,vs,fs,mat,smooth=True)

def rounded_box(kind,c,size,mat,radius=.015,segments=4):
    # This solid has a real silhouette and bevel; the material adds only microdetail.
    global SERIAL
    SERIAL+=1
    key='Rounded_'+str(SERIAL);box(key,c,size,mat)
    G[key]['bevel_radius']=min(radius,min(size)*.4)
    G[key]['bevel_segments']=segments

def prism(kind,points,z0,z1,mat):
    n=len(points);vs=[(x,y,z) for z in (z0,z1) for x,y in points]
    caps=tessellate_polygon([[Vector((x,y,0)) for x,y in points]])
    fs=[tuple(reversed(t)) for t in caps]+[tuple(i+n for i in t) for t in caps]
    fs += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    poly(kind,vs,fs,mat)

def sign(c,w,h,key,n=(0,-1,0),kind='Signs'):
    c=Vector(c);n=Vector(n).normalized()
    u=Vector((0,0,1)).cross(n).normalized();v=Vector((0,0,1))
    beam(kind,c-n*.012,c-n*.002,w,h,'PaintedSteel')
    x0,y0,x1,y1=ATLAS['rects'][key];aw,ah=ATLAS['size']
    coords=[(x0/aw,1-y1/ah),(x1/aw,1-y1/ah),(x1/aw,1-y0/ah),(x0/aw,1-y0/ah)]
    poly(kind,[c-u*w/2-v*h/2,c+u*w/2-v*h/2,c+u*w/2+v*h/2,c-u*w/2+v*h/2],
         [(0,1,2,3)],'Labels',[coords])

def quilt(c,length,width,mat='Fabric',loft=.075):
    # Bound cover, restrained sewn channels and a weighted fall over the foot.
    rounded_box('Body',c,(length,width,loft),mat,.025,5)
    for i in range(1,8):
        x=c[0]-length/2+i*length/8
        detail.tube('Body',[(x,c[1]-width/2+.045,c[2]+loft/2+.001),
                            (x,c[1]+width/2-.045,c[2]+loft/2+.001)],.0012,mat,12)
    for side in (-1,1):
        detail.tube('Body',[(c[0]-length/2+.025,c[1]+side*(width/2-.02),c[2]+loft/2-.003),
                            (c[0]+length/2-.025,c[1]+side*(width/2-.02),c[2]+loft/2-.003)],.002,mat,12)

def bunk_bed():
    for x in (-1.01,1.01):
        for y in (-.45,.45):
            cylinder((x,y,1.015),(0,0,1),.024,2.03,'PaintedSteel')
            rounded_box('Body',(x,y,.018),(.10,.10,.036),'Rubber',.007)
            collider((x,y,1.015),(.06,.06,2.03))
    for z in (.43,1.58):
        for y in (-.445,.445):
            box('Body',(0,y,z),(2.02,.05,.065),'PaintedSteel')
        for x in (-1.0,1.0):box('Body',(x,0,z),(.05,.89,.065),'PaintedSteel')
        for i in range(12):box('Body',(-.9+i*.164,0,z+.014),(.08,.84,.022),'Wood')
        rounded_box('Body',(0,0,z+.12),(1.98,.85,.19),'Fabric',.045,6)
        quilt((-.10,0,z+.238),1.65,.81)
        rounded_box('Body',(.69,0,z+.29),(.38,.59,.105),'Fabric',.045,6)
        collider((0,0,z+.10),(2.02,.90,.24))
    for y in (-.46,.46):
        cylinder((-.10,y,1.93),(1,0,0),.017,1.75,'PaintedSteel')
        collider((-.1,y,1.93),(1.75,.05,.05))
    for x in (-1.01,1.01):
        for z in (.78,1.98):cylinder((x,0,z),(0,1,0),.019,.9,'PaintedSteel')
    for x in (-.70,-.33):
        detail.tube('Body',[(x,-.54,.04),(x,-.54,1.64)],.022,'PaintedSteel',20)
        collider((x,-.54,.84),(.06,.06,1.6))
    for z in (.26,.54,.82,1.10,1.38):
        cylinder((-.515,-.54,z),(1,0,0),.019,.39,'BareSteel')
        collider((-.515,-.54,z),(.40,.065,.05))

def locker(opened=False):
    # Formed sheet body with actual interior, separate floor, shelves and door rim.
    w,d,h=.64,.55,1.94
    for x in (-w/2,w/2):box('Body',(x,0,h/2),(.025,d,h),'OlivePaint')
    box('Body',(0,d/2-.014,h/2),(w-.04,.025,h),'OlivePaint')
    for z in (.12,h-.025):box('Body',(0,0,z),(w,.55,.035),'OlivePaint')
    for z in (.6,1.35,1.66):box('Body',(0,.02,z),(.58,.50,.019),'BareSteel')
    for x in (-.23,.23):box('Body',(x,0,.055),(.07,.45,.11),'PaintedSteel')
    yaw=math.radians(-68 if opened else 0)
    pivot=Vector((-.29,-.284,0));u=Vector((math.cos(yaw),math.sin(yaw),0));v=Vector((-u.y,u.x,0))
    c=pivot+u*.29+Vector((0,0,1.05))
    # Louvres are real gaps in the lower formed sheet, with thin angled vanes.
    box('Body',c+Vector((0,0,.27)),(.58,.025,1.25),'OlivePaint',yaw)
    box('Body',c-Vector((0,0,.58)),(.58,.025,.36),'OlivePaint',yaw)
    for i in range(5):
        z=.59+i*.045
        beam('Body',pivot+u*.025+Vector((0,0,z)),pivot+u*.555+Vector((0,0,z)),.025,.025,'OlivePaint')
    for side in (-1,1):
        box('Body',c+u*side*.282,(.018,.045,1.83),'OlivePaint',yaw)
    handle=pivot+u*.52-v*.039+Vector((0,0,1.05))
    detail.tube('Body',[handle-Vector((0,0,.07)),handle-v*.018-Vector((0,0,.07)),
                         handle-v*.018+Vector((0,0,.07)),handle+Vector((0,0,.07))],.007,'BareSteel',16)
    cylinder(handle-Vector((0,0,.13)),v,.018,.012,'BareSteel',sides=24)
    for z in (.45,1.58):cylinder(pivot+Vector((0,0,z)),(0,0,1),.013,.09,'BareSteel')
    if opened:
        quilt((0,.055,.64),.40,.35,loft=.045)
        rounded_box('Body',(.08,.10,1.40),(.32,.25,.085),'Fabric',.025)
    collider((0,0,.97),(.65,.56,1.94))
    if opened:collider(list(c),(.58,.06,1.83),yaw)

def slatted_bench():
    for x in (-1.08,1.08):
        for y in (-.16,.16):
            chair_leg((x,y,.018),(x,y,.39),.035)
            rounded_box('Body',(x,y,.012),(.10,.10,.024),'BareSteel',.006)
    for y in (-.16,.16):box('Body',(0,y,.385),(2.24,.035,.05),'PaintedSteel')
    for y in (-.18,0,.18):rounded_box('Body',(0,y,.448),(2.4,.16,.075),'Wood',.009)
    collider((0,0,.435),(2.4,.53,.09))
    for x in (-1.08,1.08):collider((x,0,.20),(.10,.44,.4))

def desk(width=1.2,depth=.58):
    rounded_box('Body',(0,0,.76),(width,depth,.045),'Wood',.008)
    for x in (-width/2+.065,width/2-.065):
        for y in (-depth/2+.06,depth/2-.06):chair_leg((x,y,0),(x,y,.735),.035)
    box('Body',(0,depth/2-.035,.66),(width-.1,.025,.12),'PaintedSteel')
    collider((0,0,.76),(width,depth,.055))
    for x in (-width/2+.065,width/2-.065):collider((x,0,.36),(.065,depth-.06,.73))
    if width<1.5:
        rounded_box('Body',(width/2-.19,0,.63),(.32,depth-.04,.18),'Wood',.005)
        cylinder((width/2-.19,-depth/2-.012,.62),(1,0,0),.006,.14,'BareSteel')
        collider((width/2-.19,0,.63),(.32,depth-.04,.18))

def chair():
    for x in (-.21,.21):
        for y in (-.19,.19):chair_leg((x*1.09,y*1.16,0),(x,y,.45),.025)
    for y in (-.16,0,.16):rounded_box('Body',(0,y,.475),(.49,.145,.035),'Wood',.007)
    for x in (-.22,.22):chair_leg((x,.18,.45),(x,.245,.92),.025)
    for z in (.71,.84):rounded_box('Body',(0,.222,z),(.48,.032,.115),'Wood',.006)
    collider((0,0,.47),(.5,.48,.055));collider((0,.24,.74),(.51,.065,.42))
    for x in (-.21,.21):collider((x,0,.22),(.06,.49,.44))

def basin():
    # Ceramic rim and sloped bowl form one hollow sink, with a real drain opening.
    rings=[(.72,.51,.86),(.62,.40,.90),(.44,.26,.79),(.12,.09,.73),(.075,.055,.73)]
    vs=[];fs=[];n=48
    for w,d,z in rings:
        for i in range(n):
            a=math.tau*i/n;vs.append((w/2*math.cos(a),d/2*math.sin(a),z))
    for row in range(len(rings)-1):
        for i in range(n):fs.append((row*n+i,row*n+(i+1)%n,(row+1)*n+(i+1)%n,(row+1)*n+i))
    poly('Body',vs,fs,'Ceramic',smooth=True)
    detail.ring((0,0,.735),(0,0,1),.042,.022,.012,'BareSteel',32,'Body')
    for x in (-.26,.26):beam('Body',(x,.22,.65),(x,-.15,.79),.03,.04,'BareSteel')
    detail.tube('Body',[(0,.20,.87),(0,.20,1.12),(0,.09,1.17),(0,-.01,1.12)],.015,'BareSteel',24)
    for x in (-.14,.14):
        cylinder((x,.20,.918),(0,0,1),.034,.025,'BareSteel')
        box('Body',(x,.20,.951),(.085,.014,.014),'BareSteel')
    detail.tube('Body',[(0,0,.71),(0,0,.43),(0,.22,.43)],.032,'BareSteel',24)
    for x in (-.25,.25):collider((x,0,.80),(.12,.5,.12))
    collider((0,.21,.81),(.72,.075,.16));collider((0,-.20,.84),(.72,.075,.12))

def shower():
    detail.tube('Body',[(0,0,.40),(0,0,1.95),(0,-.19,2.11),(0,-.37,2.07)],.018,'BareSteel',24)
    detail.tube('Body',[(-.18,0,1.03),(.18,0,1.03)],.022,'BareSteel',24)
    for x in (-.13,.13):
        cylinder((x,-.025,1.03),(0,-1,0),.039,.04,'BareSteel')
        box('Body',(x,-.047,1.072),(.075,.018,.022),'BareSteel')
    cylinder((0,-.38,2.042),(0,0,1),.098,.033,'BareSteel',sides=48)
    for row in range(4):
        radius=.025+row*.02
        for j in range(12):
            a=j*math.tau/12
            cylinder((radius*math.cos(a),-.38+radius*math.sin(a),2.024),(0,0,1),.002,.004,'Rubber',sides=12)
    for z in (.65,1.62):detail.ring((0,0,z),(0,1,0),.04,.02,.025,'BareSteel',24,'Body')
    rounded_box('Body',(.40,-.10,1.15),(.22,.22,.034),'Ceramic',.01)
    rounded_box('Body',(.40,-.12,1.20),(.075,.12,.045),'Fabric',.012)
    detail.tube('Body',[(-.50,-.04,1.7),(-.50,-.10,1.7),(-.50,-.10,1.75)],.006,'BareSteel',16)

def floor_drain():
    for x in (-.19,.19):box('Body',(x,0,.012),(.025,.42,.024),'BareSteel')
    for y in (-.19,.19):box('Body',(0,y,.012),(.355,.025,.024),'BareSteel')
    for i in range(10):box('Body',(-.16+i*.035,0,.009),(.012,.35,.016),'BareSteel')
    box('Body',(0,0,-.015),(.38,.38,.016),'Rubber')

def mirror():
    rounded_box('Body',(0,0,.42),(.78,.035,.84),'PaintedSteel',.006)
    box('Body',(0,-.020,.42),(.72,.007,.78),'Mirror')

def towel_rack():
    for x in (-.48,.48):
        cylinder((x,.02,.35),(0,1,0),.03,.065,'BareSteel')
        detail.tube('Body',[(x,0,.35),(x,-.17,.35)],.013,'BareSteel',16)
    detail.tube('Body',[(-.48,-.17,.35),(.48,-.17,.35)],.016,'BareSteel',24)
    for x in (-.25,.20):
        vs=[];fs=[]
        for row in range(13):
            z=.35-row*.046
            for col in range(9):
                dx=(col/8-.5)*.35
                vs.append((x+dx,-.18-.01*math.sin(col*math.pi/2)-.016*math.sin(row*.4),z))
        for row in range(12):
            for col in range(8):
                a=row*9+col;fs.append((a,a+1,a+10,a+9))
        poly('Body',vs,fs,'Fabric',smooth=True)
        # A separate backed sheet gives the towel physical thickness and both visible sides.
        g=group('Body');a=len(g['f'])-len(fs)
        poly('Body',[(px,py+.004,pz) for px,py,pz in vs],[tuple(reversed(f)) for f in fs],'Fabric',smooth=True)

def laundry():
    for x in (-.35,.35):
        for y in (-.29,.29):chair_leg((x,y,0),(x,y,.79),.018)
    for z in (.06,.78):
        for x in (-.35,.35):box('Body',(x,0,z),(.025,.6,.025),'BareSteel')
        for y in (-.29,.29):box('Body',(0,y,z),(.7,.025,.025),'BareSteel')
    for i in range(12):
        x=-.32+i*.058
        for y in (-.29,.29):chair_leg((x,y,.08),(x,y,.77),.006,'BareSteel')
    for i in range(10):
        y=-.26+i*.058
        for x in (-.35,.35):chair_leg((x,y,.08),(x,y,.77),.006,'BareSteel')
    quilt((-.04,.02,.36),.58,.48,loft=.15);quilt((.06,-.03,.58),.57,.44,loft=.12)
    collider((0,0,.40),(.74,.64,.80))

def personal_box():
    rounded_box('Body',(0,0,.09),(.50,.34,.18),'OlivePaint',.009)
    for x in (-.225,.225):box('Body',(x,0,.185),(.015,.34,.008),'BareSteel')
    cylinder((0,-.18,.11),(1,0,0),.006,.17,'BareSteel')
    collider((0,0,.10),(.5,.34,.2))

def noticeboard():
    rounded_box('Body',(0,0,.55),(1.8,.06,1.1),'Wood',.009)
    box('Body',(0,-.034,.55),(1.7,.008,1.0),'SofaFabric')
    for i,(x,z) in enumerate(((-.60,.67),(-.22,.63),(.20,.70),(.55,.53))):
        sign((x,-.041,z),.31,.45,'Notice'+str(i),kind='Body')

def sofa():
    rounded_box('Body',(0,0,.31),(2.5,.9,.46),'SofaFabric',.055,6)
    for x in (-1.13,1.13):rounded_box('Body',(x,0,.57),(.21,.95,.61),'SofaFabric',.055,6)
    for x in (-.75,0,.75):
        rounded_box('Body',(x,-.035,.575),(.70,.66,.15),'SofaFabric',.045,6)
        rounded_box('Body',(x,.30,.85),(.72,.23,.67),'SofaFabric',.050,6)
    for x in (-.96,.96):
        for y in (-.27,.27):cylinder((x,y,.09),(0,0,1),.035,.18,'Wood')
    collider((0,0,.34),(2.5,.95,.68));collider((0,.33,.86),(2.5,.3,.68))

def coffee_table():
    rounded_box('Body',(0,0,.43),(1.5,.68,.05),'Wood',.015)
    for x in (-.58,.58):
        for y in (-.24,.24):chair_leg((x,y,0),(x,y,.4),.027)
    collider((0,0,.43),(1.5,.68,.06))
    for x in (-.58,.58):collider((x,0,.20),(.06,.56,.40))
    rounded_box('Body',(.30,.04,.482),(.24,.33,.035),'Fabric',.006)

def television():
    rounded_box('Body',(0,0,.63),(1.75,.18,1.05),'PaintedSteel',.032)
    box('Body',(-.045,-.094,.66),(1.50,.009,.85),'Screen')
    for i in range(9):box('Body',(.805,-.099,.40+i*.028),(.03,.009,.012),'Rubber')
    for x in (-.42,.42):chair_leg((x,.10,.39),(x,.23,.22),.05)
    collider((0,0,.63),(1.75,.19,1.05))

def table_tennis():
    rounded_box('Body',(0,0,.73),(2.74,1.525,.055),'OlivePaint',.005)
    for y in (-.753,.753):box('Body',(0,y,.76),(2.70,.020,.0025),'Ceramic')
    for x in (-1.36,1.36):box('Body',(x,0,.76),(.018,1.525,.0025),'Ceramic')
    box('Body',(0,0,.762),(.015,1.51,.003),'Ceramic')
    for x in (-.82,.82):
        for y in (-.48,.48):chair_leg((x,y,.07),(x,y,.7),.045)
        beam('Body',(x,-.48,.20),(x,.48,.20),.025,.03,'BareSteel')
    for y in (-.78,.78):cylinder((0,y,.827),(0,0,1),.007,.15,'BareSteel')
    # An open net, no opaque rectangle pretending to be woven mesh.
    for i in range(59):
        y=-.77+i*1.54/58
        detail.tube('Body',[(0,y,.77),(0,y,.915)],.0008,'Fabric',12)
    for z in (.77,.795,.82,.845,.87,.895,.918):detail.tube('Body',[(0,-.78,z),(0,.78,z)],.0009,'Fabric',12)
    collider((0,0,.73),(2.74,1.525,.06))
    for x in (-.82,.82):collider((x,0,.36),(.08,1.04,.72))
    ball((.61,-.21,.785),.02)

def billiard():
    rounded_box('Body',(0,0,.54),(2.72,1.53,.53),'Wood',.02)
    for x in (-1.02,1.02):
        for y in (-.48,.48):
            cylinder((x,y,.27),(0,0,1),.105,.54,'Wood',sides=32)
            cylinder((x,y,.027),(0,0,1),.12,.054,'BareSteel',sides=32)
    # The concave baize perimeter leaves six actual recessed pockets.
    points=[(-1.19,-.56),(-1.08,-.68),(-.13,-.68),(-.07,-.58),(.07,-.58),(.13,-.68),(1.08,-.68),(1.19,-.56),
            (1.19,.56),(1.08,.68),(.13,.68),(.07,.58),(-.07,.58),(-.13,.68),(-1.08,.68),(-1.19,.56)]
    prism('Body',points,.809,.854,'Felt')
    for y in (-.72,.72):
        for x in (-.64,.64):rounded_box('Body',(x,y,.89),(1.07,.10,.085),'Felt',.02)
    for x in (-1.245,1.245):rounded_box('Body',(x,0,.89),(.10,1.10,.085),'Felt',.02)
    for x,y in ((-1.2,-.66),(0,-.67),(1.2,-.66),(-1.2,.66),(0,.67),(1.2,.66)):
        detail.ring((x,y,.845),(0,0,1),.095,.06,.045,'Rubber',32,'Body')
        cylinder((x,y,.76),(0,0,1),.056,.07,'Rubber')
    for i,(x,y) in enumerate(((.45,.05),(.5,.09),(.5,.0),(-.7,-.12))):ball((x,y,.883),.028,'Ceramic' if i%2 else 'Yellow')
    collider((0,0,.55),(2.75,1.58,.60))
    for x in (-1.02,1.02):collider((x,0,.27),(.23,1.20,.54))

def cue_rack():
    for z in (.30,1.50):rounded_box('Body',(0,0,z),(.90,.08,.11),'Wood',.006)
    for i in range(5):
        x=-.32+i*.16
        detail.tube('Body',[(x,-.085,.05),(x+.01,-.095,1.48)],.008,'Wood',16)
    collider((0,0,.9),(.92,.14,1.7))

def kitchen():
    rounded_box('Body',(0,0,.46),(3.5,.67,.88),'OlivePaint',.01)
    rounded_box('Body',(0,0,.93),(3.60,.75,.06),'Ceramic',.015)
    for x in (-1.36,-.67,0,.67,1.36):
        rounded_box('Body',(x,-.349,.48),(.63,.024,.70),'OlivePaint',.006)
        cylinder((x,-.37,.73),(1,0,0),.006,.19,'BareSteel')
    for x in (-1.0,1.0):
        cylinder((x,0,1.12),(0,0,1),.115,.28,'BareSteel',sides=40)
        cylinder((x,0,1.275),(0,0,1),.13,.03,'BareSteel',sides=40)
        detail.tube('Body',[(x+.06,-.07,1.07),(x+.16,-.11,1.14),(x+.13,-.15,1.18)],.011,'BareSteel',16)
    collider((0,0,.47),(3.6,.75,.96))

def refrigerator():
    rounded_box('Body',(0,0,.86),(.79,.72,1.72),'Ceramic',.022)
    for z,h in ((.46,.72),(1.28,.84)):
        rounded_box('Body',(0,-.377,z),(.75,.038,h),'Ceramic',.017)
        detail.tube('Body',[(-.27,-.41,z-.12),(-.27,-.45,z-.12),(-.27,-.45,z+.12),(-.27,-.41,z+.12)],.009,'BareSteel',16)
    collider((0,0,.86),(.79,.81,1.72))

def water_dispenser():
    rounded_box('Body',(0,0,.55),(.39,.40,1.10),'Ceramic',.015)
    rounded_box('Body',(0,-.21,.66),(.24,.015,.32),'Rubber',.004)
    for x in (-.063,.063):
        cylinder((x,-.241,.77),(0,1,0),.013,.038,'BareSteel')
        rounded_box('Body',(x,-.255,.81),(.024,.032,.024),'Yellow' if x<0 else 'OlivePaint',.005)
    cylinder((0,0,1.31),(0,0,1),.145,.37,'OlivePaint',sides=40)
    collider((0,0,.57),(.40,.46,1.14))

def fixture():
    rounded_box('Body',(0,0,0),(1.25,.23,.085),'PaintedSteel',.006)
    rounded_box('Body',(0,0,-.054),(1.16,.18,.029),'LampGlass',.008)
    for x in (-.63,.63):box('Body',(x,0,-.008),(.032,.25,.1),'BareSteel')

def merge_groups():
    # Apply local bevels before combining; all subparts retain material/UV ownership.
    source=list(G.items());out=dict(v=[],f=[],m=[],uv=[],smooth=[])
    for key,g in source:
        mesh=bpy.data.meshes.new('_part');mesh.from_pydata(g['v'],[],g['f']);mesh.update()
        names=list(dict.fromkeys(g['m']))
        for mat in names:mesh.materials.append(MATS[mat])
        uv=mesh.uv_layers.new(name='UVMap')
        for face,mat,coords,smooth in zip(mesh.polygons,g['m'],g['uv'],g['smooth']):
            face.material_index=names.index(mat);face.use_smooth=smooth
            dims=[i for i in range(3) if i!=max(range(3),key=lambda k:abs(face.normal[k]))]
            scale=.42 if mat in ('Linen','Terry','Hem') else .48 if mat in ('Fabric','SofaFabric','Felt') else 1.72 if mat=='Wood' else 2.
            for j,li in enumerate(face.loop_indices):
                p=mesh.vertices[mesh.loops[li].vertex_index].co
                uv.data[li].uv=coords[j] if coords is not None else (p[dims[0]]/scale,p[dims[1]]/scale)
        obj=bpy.data.objects.new('_part',mesh);bpy.context.scene.collection.objects.link(obj)
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
        if 'bevel_radius' in g:
            bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
            bevel=obj.modifiers.new('Manufactured edge','BEVEL');bevel.width=g['bevel_radius'];bevel.segments=g['bevel_segments'];bevel.limit_method='ANGLE';bevel.harden_normals=True
            bpy.ops.object.modifier_apply(modifier=bevel.name)
            weighted=obj.modifiers.new('Face weighted normals','WEIGHTED_NORMAL');weighted.keep_sharp=True
            bpy.ops.object.modifier_apply(modifier=weighted.name)
        mesh=obj.data;offset=len(out['v']);out['v'] += [tuple(v.co) for v in mesh.vertices]
        out['f'] += [tuple(offset+i for i in f.vertices) for f in mesh.polygons]
        out['m'] += [names[f.material_index] for f in mesh.polygons]
        out['smooth'] += [f.use_smooth for f in mesh.polygons]
        out['uv'] += [[tuple(mesh.uv_layers.active.data[li].uv) for li in f.loop_indices] for f in mesh.polygons]
        bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(mesh)
    return out

def export_mesh(name,g,room_id=None,prototype=None,collision=True,nanite=True,kind='',hulls=()):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(g['v'],[],g['f']);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj)
    names=list(dict.fromkeys(g['m']))
    for mat in names:mesh.materials.append(MATS[mat])
    uv=mesh.uv_layers.new(name='UVMap');woodlocal=mesh.uv_layers.new(name='DetailLocal')
    age=mesh.color_attributes.new(name='ServiceAge',type='FLOAT_COLOR',domain='CORNER')
    for face,mat,coords,smooth in zip(mesh.polygons,g['m'],g['uv'],g['smooth']):
        face.material_index=names.index(mat);face.use_smooth=smooth
        dims=[i for i in range(3) if i!=max(range(3),key=lambda k:abs(face.normal[k]))]
        scale=.42 if mat in ('Linen','Terry','Hem') else .48 if mat in ('Fabric','SofaFabric','Felt') else .075 if mat=='V2_CeramicFractureCore' else 1.28 if 'WallRelief' in mat else 2.
        for j,li in enumerate(face.loop_indices):
            p=mesh.vertices[mesh.loops[li].vertex_index].co
            uv.data[li].uv=coords[j] if coords is not None else (p[dims[0]]/scale,p[dims[1]]/scale)
            woodlocal.data[li].uv=(uv.data[li].uv.x-10,uv.data[li].uv.y-10)
            age.data[li].color=(.96,.96,.96,1) if mat=='Wood' else (.09+.08*max(0,math.sin(p.x*.8+p.y*.65+p.z*2.3)),0,0,1)
    mesh.uv_layers.active_index=0
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    if kind not in ('Tiles','Signs','Body'):
        bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    if kind in ('Walls','Floors','Roof','Beams','Platforms'):
        bevel=obj.modifiers.new('Structural arris','BEVEL');bevel.width=.005;bevel.segments=2;bevel.limit_method='ANGLE'
        bpy.ops.object.modifier_apply(modifier=bevel.name)
    tri=obj.modifiers.new('FBX triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    mesh=obj.data;data=mesh.uv_layers[0].data
    # Author UVs for new triangulation side faces using a non-degenerate dominant-axis projection.
    for face in mesh.polygons:
        ids=list(face.loop_indices);a,b,c=(data[i].uv.copy() for i in ids)
        if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))>1.e-12:continue
        dims=[i for i in range(3) if i!=max(range(3),key=lambda k:abs(face.normal[k]))]
        for li in ids:
            p=mesh.vertices[mesh.loops[li].vertex_index].co;data[li].uv=(p[dims[0]]/2,p[dims[1]]/2)
    collision_objects=[]
    for ci,(c,size,yaw) in enumerate(hulls):
        dx,dy,dz=[s/2 for s in size];co,si=math.cos(yaw),math.sin(yaw)
        vs=[(c[0]+x*co-y*si,c[1]+x*si+y*co,c[2]+z) for x,y,z in
            [(-dx,-dy,-dz),(dx,-dy,-dz),(dx,dy,-dz),(-dx,dy,-dz),(-dx,-dy,dz),(dx,-dy,dz),(dx,dy,dz),(-dx,dy,dz)]]
        cm=bpy.data.meshes.new('UCX_'+name+'_'+str(ci));cm.from_pydata(vs,[],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]);cm.update()
        cu=bpy.data.objects.new(cm.name,cm);bpy.context.scene.collection.objects.link(cu);cu.select_set(True);collision_objects.append(cu)
    fbx=OUT/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
    records.append(dict(name=name,kind=kind,room_id=room_id,prototype=prototype,fbx=str(fbx),
        materials={'RS_'+k:MAPPING[k] for k in names},triangles=len(mesh.polygons),collision=collision,
        nanite=nanite,simple_collision_hulls=len(hulls),asset=CFG['ue_base']+'/Meshes/'+name))
    room_offsets={r['id']:offset for r,offset in zip(CFG['rooms'],CFG['preview_placements_m'])}
    source_offset=room_offsets.get(room_id,[0,0,0])
    if prototype:
        index=list(PROTOTYPES).index(prototype)
        source_offset=[-13+(index%6)*5,-35-(index//6)*4,0]
    elif room_id=='Link':source_offset=[16,0,0]
    obj.location=source_offset
    for cu in collision_objects:
        cu.location=source_offset;cu.hide_render=True;cu.hide_viewport=True
    print('STAFF_LIVING_EXPORTED',name,len(mesh.polygons),flush=True)

PROTOTYPES={'BunkBed':bunk_bed,'Locker':lambda:locker(False),'LockerOpen':lambda:locker(True),
 'ChangingBench':slatted_bench,'Desk':desk,'Chair':chair,'WashBasin':basin,'ShowerFittings':shower,
 'FloorDrain':floor_drain,'Mirror':mirror,'TowelRack':towel_rack,'LaundryBasket':laundry,
 'PersonalBox':personal_box,'Noticeboard':noticeboard,'Sofa':sofa,'CoffeeTable':coffee_table,
 'Television':television,'TableTennis':table_tennis,'BilliardTable':billiard,'CueRack':cue_rack,
 'KitchenCounter':kitchen,'Refrigerator':refrigerator,'WaterDispenser':water_dispenser,
 'DiningTable':lambda:desk(1.85,.80),'LampFixture':fixture}
for key,fn in PROTOTYPES.items():
    G={};HULLS=[];fn();merged=merge_groups()
    export_mesh('SM_Staff_'+key,merged,prototype=key,kind='Body',hulls=HULLS,
                collision=bool(HULLS),nanite=key not in ('Mirror','TowelRack','LampFixture','FloorDrain'))

def wall(a,b,height,openings=(),tiles=True):
    wall_segment(a,b,height,openings,tiles)

def neck(x0,x1,y,height=3.4):
    paving(x0,y-2,x1,y+2)
    wall((x0,y-2),(x1,y-2),height);wall((x1,y+2),(x0,y+2),height)
    outside=x0 if x0<0 else x1
    wall((outside,y-2),(outside,y+2),height,[dict(center=2,width=3,height=2.8)])
    box('Roof',((x0+x1)/2,y,height+.14),(x1-x0+.28,4.28,.28),'Concrete')

for room in CFG['rooms']:
    G={};HULLS=[];ROOM['id']=room['id'];ROOM['height_m']=room['height'];ROOM['ceilings']=[]
    outline=room['outline'];h=room['height'];rid=room['id'];prefix=room['prefix']
    prism('Floors',outline,-.30,-.018,'Concrete')
    prism('FloorFinish',outline,-.018,0,'Linoleum' if rid!='StaffChangingShowers' else 'Ceramic')
    prism('Roof',outline,h,h+.30,'Concrete')
    ports=room['ports']
    for a,b in zip(outline,outline[1:]+outline[:1]):
        openings=[]
        if a[0]==b[0] and abs(a[1]-b[1])>10:
            yy=ports[0]['position'][1];openings=[dict(center=abs(yy-a[1]),width=3,height=2.8)]
        wall(a,b,h,openings)
    xmin=min(p[0] for p in outline);xmax=max(p[0] for p in outline);yy=ports[0]['position'][1]
    neck(xmin-2,xmin,yy);neck(xmax,xmax+2,yy)
    # Perimeter ceiling services, fixed to real beams and kept away from door headroom.
    for y in (-1.28,1.28):
        detail.tube('Services',[(xmin+.35,yy+y,h-.40),(xmax-.35,yy+y,h-.40)],.027,'PipeEnamel',24)
        for x in range(int(xmin)+1,int(xmax),4):
            beam('Services',(x,yy+y,h-.43),(x,yy+y,h-.04),.025,.025,'BareSteel')
    if rid=='StaffDormitory':
        centers=[-9.5,-.5,9.]
        for side in (-1,1):
            opens=[dict(center=c+14,width=1.45,height=2.35) for c in centers]
            wall((-14,side*2),(14,side*2),3.4,opens)
            for x in (-5,4):wall((x,side*2),(x,side*10),3.4)
            box('BedroomCeilings',(0,side*6,3.51),(27.75,7.72,.22),'Concrete')
            for col,cx in enumerate(centers):
                sign((cx+.99,side*1.835,2.00),.40,.24,'Room'+str(101+(0 if side<0 else 3)+col),(0,-side,0))
        for x in (-11,-3,5,12):box('Beams',(x,0,4.28),(.26,3.55,.42),'Concrete')
        sign((-12,-1.82,2.75),1.10,.40,'Dormitory',(0,1,0))
        sign((12,1.82,2.75),.90,.32,'ToChanging',(0,-1,0))
    elif rid=='StaffChangingShowers':
        for side in (-1,1):
            xs=(-8,0,8) if side>0 else (-6,6)
            wall((-12,side*1.8),(12,side*1.8),3.55,
                 [dict(center=x+12,width=1.8 if side<0 else 1.6,height=2.45) for x in xs])
        # Dry-room louvred benches and visible wet-room partitions; no live water.
        for x in (-7.85,-3.95,-.05,3.85,7.75):
            wall((x,-10.9),(x,-6.45),2.40,tiles=True)
        for x in (-11.8,-7.8,-3.9,0,3.9,7.8,11.8):
            for y in (-10.7,-6.5):cylinder((x,y,2.43),(0,0,1),.018,.08,'BareSteel','ShowerHardware')
        for i,x in enumerate((-9.8,-5.9,-2,1.9,5.8,9.7)):
            box('WetThresholds',(x,-6.5,.022),(3.66,.06,.045),'Ceramic')
            sign((x,-10.795,2.55),.35,.22,'Shower'+str(i+1),(0,1,0))
        # Small tile joints and drainage rails follow the wet area, leaving no raised black decal strips.
        for x in range(-11,12):box('WetGrout',(x,-6.4,.002),(.005,8.2,.004),'Mortar')
        for y in range(-10,-2):box('WetGrout',(0,y,.002),(23.5,.005,.004),'Mortar')
        sign((-10.2,1.64,2.75),1.25,.42,'Changing',(0,-1,0))
        sign((2.4,-1.63,2.75),1.35,.42,'Showers',(0,1,0))
        for x in (-8,0,8):box('Beams',(x,0,4.37),(.28,21.6,.46),'Concrete')
        for y in (3.1,9.35):
            detail.tube('Services',[(-11.3,y,3.3),(11.3,y,3.3)],.027,'PipeEnamel',24)
    else:
        # L-shaped room, low lounge platform and canopy contrast with the higher games hall.
        box('Platforms',(-9,8.7,.22),(10,5.6,.44),'Concrete')
        box('PlatformFinish',(-9,8.7,.446),(9.98,5.58,.012),'Wood')
        for step in range(3):
            top=(step+1)*.15;y=4.80+(step+.5)*.35
            box('Platforms',(-9,y,top/2),(2.6,.35,top),'Concrete')
            box('Nosing',(-9,y-.16,top+.003),(2.57,.018,.006),'BareSteel')
        box('LoungeCanopy',(-9,8.7,4.15),(10,5.6,.24),'Concrete')
        for x in (-13.4,-4.6):
            box('Columns',(x,8.7,2.23),(.23,.23,3.56),'PaintedSteel')
        # The front edge is a low step, so the opening remains broad and usable.
        for y in (6.0,11.4):box('LoungeTrim',(-9,y,.46),(9.9,.03,.07),'BareSteel')
        for x in (-12,-4,4,12):box('Beams',(x,-2,5.24),(.3,19.5,.52),'Concrete')
        # Dining-side low ceiling distinguishes the quiet meal bay from games.
        box('DiningCanopy',(3.0,9.75,3.65),(11.5,4.5,.22),'Concrete')
        sign((-12,-11.83,2.55),1.65,.56,'Recreation',(0,1,0))
        sign((11,-11.79,2.10),1.25,.40,'Meals',(0,1,0))
        sign((-5.5,11.78,2.5),1.10,.37,'Quiet',(0,-1,0))
    sign((ports[1]['position'][0]-.42,ports[1]['position'][1]-1.81,2.96),.48,.28,'Exit',(0,1,0))
    for kind,g in G.items():
        if not g['f']:continue
        no_collision=kind in ('Tiles','Frames','Services','Signs','Nosing','ShowerHardware','WetGrout','LoungeTrim')
        export_mesh('SM_Staff_'+prefix+'_'+kind,g,room_id=rid,kind=kind,
                    collision=not no_collision,nanite=kind not in ('Signs','Nosing','Services','ShowerHardware','WetGrout'))

# A shared four-metre link joins each pair of complete room ports in the theme preview.
G={};ROOM['id']='StaffLivingLink';ROOM['height_m']=3.4
paving(0,-2,4,2);wall((0,-2),(4,-2),3.4);wall((4,2),(0,2),3.4)
box('Roof',(2,0,3.54),(4,4.28,.28),'Concrete')
for kind,g in G.items():
    export_mesh('SM_Staff_Link_'+kind,g,room_id='Link',kind=kind,collision=kind not in ('Tiles','Frames'),nanite=True)

# The editable source also contains the actual room furniture, not overlapping catalogue parts.
for room,offset in zip(CFG['rooms'],CFG['preview_placements_m']):
    for part in room['furniture']:
        source=bpy.data.objects['SM_Staff_'+part['prototype']]
        inst=source.copy();inst.data=source.data;inst.name=room['id']+'_'+part['id']
        bpy.context.scene.collection.objects.link(inst)
        inst.location=Vector(offset)+Vector(part['position']);inst.rotation_euler.z=math.radians(part['yaw_blender_deg'])
    for light in room['lights']:
        source=bpy.data.objects['SM_Staff_LampFixture'];inst=source.copy();inst.data=source.data
        inst.name=room['id']+'_Lamp_'+light['id'];bpy.context.scene.collection.objects.link(inst)
        inst.location=Vector(offset)+Vector(light['position'])+Vector((0,0,.11))
for item in [r for r in records if r['room_id']=='Link']:
    source=bpy.data.objects[item['name']];inst=source.copy();inst.data=source.data
    inst.name=source.name+'_Second';bpy.context.scene.collection.objects.link(inst);inst.location=(48,0,0)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'StaffLivingTheme_Source.blend'))
(OUT/'manifest.json').write_text(json.dumps(dict(objects=records,revision=CFG['revision'],tests_run=False,
    rendered=False,source_units='metres; UE centimetres',coordinates='Blender (x,y,z) -> Unreal (100*x,-100*y,100*z)',
    ceramic_source='DungeonTileFracture20260922 through CorridorSurfaces',furniture_original=True),indent=2),encoding='utf-8')
print('STAFF_LIVING_SOURCE_SAVED',len(records),flush=True)
