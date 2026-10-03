"""Baked scene polish for the three complete staff rooms. No render or game run."""
from pathlib import Path
SCRIPT=Path(__file__).resolve().parent
import json
if json.loads((SCRIPT.parent/'Config/room.json').read_text('utf8')).get('room_details_revision',0)>=5:
    current=SCRIPT/'author_room_details_v5.py'
    exec(compile(current.read_text('utf8'),str(current),'exec'))
    raise SystemExit(0)
_STAFF_REFINEMENT_HELPERS=True
entry=SCRIPT/'author_living.py'
exec(compile(entry.read_text('utf8').split('for key,fn in PROTOTYPES.items():')[0],str(entry),'exec'))
import random,copy
from dormitory_layout_polish_v4 import make_layouts
OUT=ROOT/'ScenePolishV4/Authored';OUT.mkdir(parents=True,exist_ok=True)
BASE=CFG['ue_base']+'/ScenePolishV4';records=[];prototypes={}
for key in ('Linen','Terry','Hem','Carpet'):
    MAPPING[key]=CFG['ue_base']+'/RefinementV3/Materials/'+('MI_Staff_NavyCarpet_V3' if key=='Carpet' else 'M_Staff_'+key+'_V3')
    MATS[key]=bpy.data.materials.new('RS_'+key)
for key in ('BookPaper','BookGreen','BookBlue','BookRed'):
    MAPPING[key]=CFG['ue_base']+'/DormitoryVariantsV2/Materials/M_Dorm_'+key;MATS[key]=bpy.data.materials.new('RS_'+key)
for key in ('JugPlastic','JugWater','CueMaple','CueGrip','CueTip','PoolIvory','PoolBlue','PoolRed','TVGlass','CarpetBinding'):
    MAPPING[key]=BASE+'/Materials/M_Staff_'+key+'_V4';MATS[key]=bpy.data.materials.new('RS_'+key)

# Reuse the accepted fabric/plumbing author without running its old delivery.
v3=SCRIPT/'author_refinement_v3.py';code=v3.read_text('utf8')
exec(compile(code[code.index('def surface_solid'):code.index('def shower_v3')],str(v3),'exec'))

def bed_v4(variant):
    # Constrain the duvet to the mattress envelope; keep its baked loose folds.
    original_bunk();remove_fabric();rng=random.Random(610024+variant*53)
    for level,z in enumerate((.43,1.58)):
        rounded_box('Body',(0,0,z+.12),(1.965,.84,.19),'Linen',.057,8)
        for side in (-1,1):
            detail.tube('Body',[(-.94+i*1.88/56,side*.412,z+.157) for i in range(57)],.0032,'Hem',12)
        nx,ny=60,34;pts=[];uvs=[];phase=rng.uniform(0,math.tau)
        length=(1.64,1.39,1.66,1.50)[variant];width=(.75,.72,.76,.73)[variant]
        centerx=(-.07,-.16,-.065,-.13)[variant]
        for i in range(nx+1):
            u=i/nx;x=centerx+(u-.5)*length
            for j in range(ny+1):
                v=j/ny
                # Bounded asymmetric hem: maximum |Y| 38.8cm, inside 42cm mattress.
                y=(v-.5)*width+.009*math.sin(u*11+phase)*math.sin(math.pi*u)
                y+=.004*math.sin(v*math.pi)*math.sin(u*math.pi)
                envelope=math.sin(math.pi*u)**.5*math.sin(math.pi*v)**.45
                ridge=(.018+.007*variant)*(.5+.5*math.sin(21*u+9*v+phase))**3
                diagonal=.025*math.exp(-((v-.28-.32*u)/.085)**2)
                rumple=.045*math.exp(-((u-.22)/.23)**2)*(.5+.5*math.sin(v*28+u*8+phase))**2
                turn=.075*math.exp(-((u-.88)/.105)**2)*(v**3 if (variant+level)%2 else (1-v)**3)
                pts.append((x,y,z+.241+envelope*(ridge+diagonal+rumple)+turn));uvs.append((x/.42,y/.42))
        boundary=surface_solid(pts,nx,ny,uvs,thickness=.022);sewn_hem(pts,boundary,radius=.0026)
        px=.69+rng.uniform(-.020,.018);py=rng.uniform(-.025,.025)
        angle=math.radians(rng.uniform(-5,5));co,si=math.cos(angle),math.sin(angle)
        nx,ny=28,32;pts=[];uvs=[]
        for i in range(nx+1):
            u=i/nx;a=(u-.5)*.40
            for j in range(ny+1):
                v=j/ny;b=(v-.5)*.59
                puff=.10*(math.sin(math.pi*u)*math.sin(math.pi*v))**.43
                pts.append((px+a*co-b*si,py+a*si+b*co,z+.236+puff+.005*math.sin(v*28+phase)*math.sin(math.pi*u)))
                uvs.append((a/.42,b/.42))
        boundary=surface_solid(pts,nx,ny,uvs,thickness=.022);sewn_hem(pts,boundary,radius=.0022)

def mirror_v4():
    rounded_box('Body',(0,.013,.42),(.78,.100,.84),'PaintedSteel',.010,6)
    # The reflective slab is in front of the solid frame, not embedded inside it.
    rounded_box('Body',(0,-.044,.42),(.718,.006,.775),'Mirror',.002,3)
    for x in (-.33,.33):
        for z in (.09,.75):
            box('Body',(x,.065,z),(.065,.030,.090),'BareSteel')
            cylinder((x,-.038,z),(0,1,0),.007,.005,'BareSteel',sides=24)
    box('Body',(0,.065,.69),(.66,.030,.07),'BareSteel')

def solid(c,size,mat='Wood'):
    rounded_box('Body',c,size,mat,.004,3);collider(c,size)

def books(x0,y,z,count,seed):
    rr=random.Random(seed);x=x0
    for i in range(count):
        t=rr.uniform(.025,.043);h=rr.uniform(.195,.265);d=rr.uniform(.12,.17)
        color=('BookGreen','BookBlue','BookRed')[rr.randrange(3)]
        # Page block stops short of both covers and the separate spine.
        rounded_box('Body',(x+t/2,y+.003,z+h/2),(t-.008,d-.016,h-.012),'BookPaper',.0015,2)
        for side in (-1,1):rounded_box('Body',(x+t/2+side*(t/2-.0015),y,z+h/2),(.003,d,h),color,.001,2)
        rounded_box('Body',(x+t/2,y-d/2+.002,z+h/2),(t,.004,h),color,.001,2)
        for zz in (.04,h-.035):box('Body',(x+t/2,y-d/2-.0007,z+zz),(t*.78,.0014,.004),'BookPaper')
        x+=t+rr.uniform(.006,.011)
    for i in range(2):
        zz=z+.010+i*.026;cx=x+.125+i*.007;color='BookBlue' if i else 'BookRed'
        rounded_box('Body',(cx,y+.004,zz),(.224,.143,.014),'BookPaper',.0015,3)
        # 0.5mm physical separation avoids coincident cover/page faces.
        for side in (-1,1):rounded_box('Body',(cx,y,zz+side*.0085),(.240,.165,.002),color,.0006,2)
        box('Body',(cx,y-.080,zz),(.240,.004,.014),color)

def bookcase_v4():
    for x in (-.465,.465):solid((x,0,1.0),(.03,.40,1.94),'OlivePaint')
    solid((0,.185,1.0),(.90,.03,1.94),'OlivePaint')
    for z in (.11,.82,1.20,1.57,1.96):solid((0,0,z),(.96,.40,.035))
    for x in (-.37,.37):solid((x,0,.052),(.065,.32,.105),'PaintedSteel')
    for i,z in enumerate((.84,1.22,1.59)):books(-.405,-.015,z,9-i*2,41+i)
    for z in (.26,.68):cylinder((-.439,-.215,z),(0,0,1),.010,.067,'BareSteel')

def bookshelf_v4():
    for x in (-.405,.405):
        for y in (-.145,.145):solid((x,y,.92),(.028,.028,1.84),'PaintedSteel')
    for z in (.14,.56,.98,1.40,1.81):
        solid((0,0,z),(.88,.34,.028));solid((0,.15,z-.037),(.81,.026,.046),'OlivePaint')
    for i,z in enumerate((.578,.998,1.418)):books(-.34,-.005,z,5+i%3,64+i)
    for x in (-.385,.385):
        solid((x,-.004,.198),(.012,.27,.024),'BareSteel')
        for y in (-.095,.095):cylinder((x,y,.205),(1,0,0),.011,.021,'BareSteel',sides=16)
    for side in (-1,1):detail.tube('Body',[(side*.40,.158,.19),(-side*.40,.158,1.75)],.006,'BareSteel',12)

def shelf_drawer_v4():
    solid((0,-.177,.338),(.784,.024,.322));rounded_box('Body',(0,-.192,.338),(.660,.012,.244),'Wood',.009,4)
    for x in (-.364,.364):solid((x,-.020,.324),(.020,.288,.282))
    solid((0,.123,.324),(.728,.018,.282));solid((0,-.020,.174),(.728,.288,.018))
    for x in (-.374,.374):solid((x,-.004,.199),(.008,.26,.018),'BareSteel')
    detail.tube('Body',[(-.085,-.201,.338),(-.085,-.231,.338),(.085,-.231,.338),(.085,-.201,.338)],.007,'BareSteel',18)
    for x in (-.085,.085):cylinder((x,-.201,.338),(0,1,0),.013,.008,'BareSteel',sides=24)
    # Drawer books lie down; upright 26cm books would exceed its 28cm cavity.
    books(-.30,-.028,.184,2,93)

def lathe(c,profile,mat,sides=64):
    x,y,z=c;vs=[];fs=[]
    for zz,r in profile:
        for j in range(sides):
            a=j*math.tau/sides;vs.append((x+r*math.cos(a),y+r*math.sin(a),z+zz))
    for row in range(len(profile)-1):
        for j in range(sides):fs.append((row*sides+j,row*sides+(j+1)%sides,(row+1)*sides+(j+1)%sides,(row+1)*sides+j))
    fs.extend([tuple(reversed(range(sides))),tuple((len(profile)-1)*sides+j for j in range(sides))])
    poly('Body',vs,fs,mat,smooth=True)

def cue(c):
    x,y,z=c
    lathe(c,[(0,.016),(.012,.017),(.032,.015)],'Rubber',32)
    lathe((x,y,z+.032),[(0,.0145),(.32,.013),(.63,.011)],'BookRed',40)
    # Turned grip ribs and brass joint rings read at close player distance.
    for i in range(22):detail.ring((x,y,z+.085+i*.012),(0,0,1),.0148-i*.00003,.0130-i*.00003,.005,'CueGrip',32,'Body')
    for zz in (.35,.64):cylinder((x,y,z+zz),(0,0,1),.013,.009,'BareSteel',sides=40)
    lathe((x,y,z+.65),[(0,.0105),(.35,.0079),(.72,.0056),(.80,.0048)],'CueMaple',48)
    cylinder((x,y,z+1.459),(0,0,1),.0048,.018,'PoolIvory',sides=40)
    cylinder((x,y,z+1.472),(0,0,1),.0049,.008,'CueTip',sides=40)

def cue_rack_v4():
    for z in (.27,1.48):
        rounded_box('Body',(0,-.003,z),(.98,.12,.105),'Wood',.010,6)
        for x in (-.43,.43):
            box('Body',(x,.063,z),(.065,.015,.15),'BareSteel')
            for dz in (-.04,.04):detail.fastener((x,-.071,z+dz),(0,-1,0),.006,'Body')
    for i in range(5):
        x=-.36+i*.18;y=-.13
        rounded_box('Body',(x,y,.267),(.092,.13,.065),'Wood',.013,5)
        detail.ring((x,y,.298),(0,0,1),.026,.018,.023,'Rubber',40,'Body')
        detail.tube('Body',[(x,-.048,1.48),(x,-.13,1.48)],.009,'BareSteel',20)
        # Open retaining clip, visibly connected to the upper rail.
        arc=[(x+.018*math.cos(a),y+.018*math.sin(a),1.48) for a in [math.radians(-20+j*220/24) for j in range(25)]]
        detail.tube('Body',arc,.004,'Rubber',16);cue((x,y,.309))
    collider((0,-.07,.94),(1.0,.24,1.72))

def billiard_v4():
    # Separate slate apron, rail cap and adjustable legs; six real open pockets.
    for y in (-.78,.78):rounded_box('Body',(0,y,.51),(2.74,.040,.45),'Wood',.014,6)
    for x in (-1.36,1.36):rounded_box('Body',(x,0,.51),(.040,1.52,.45),'Wood',.014,6)
    for x in (-.99,.99):
        for y in (-.49,.49):
            lathe((x,y,0),[(.025,.12),(.07,.12),(.08,.095),(.15,.088),(.28,.067),(.43,.11)],'Wood',64)
            cylinder((x,y,.025),(0,0,1),.125,.05,'BareSteel',sides=64)
            detail.ring((x,y,.095),(0,0,1),.092,.067,.018,'BareSteel',48,'Body')
    points=[(-1.19,-.56),(-1.08,-.68),(-.13,-.68),(-.07,-.58),(.07,-.58),(.13,-.68),(1.08,-.68),(1.19,-.56),
        (1.19,.56),(1.08,.68),(.13,.68),(.07,.58),(-.07,.58),(-.13,.68),(-1.08,.68),(-1.19,.56)]
    prism('Body',points,.746,.786,'BareSteel')
    prism('Body',points,.786,.824,'Felt')
    for y in (-.755,.755):
        for x in (-.66,.66):
            rounded_box('Body',(x,y,.847),(1.07,.135,.10),'Wood',.017,6)
            rounded_box('Body',(x,y*.90,.843),(1.035,.075,.074),'Felt',.015,6)
        for x in (-.94,-.48,.48,.94):
            # Diamond-shaped sight inlays sit visibly above the rail surface.
            prism('Body',[(x-.012,y),(x,y-.010),(x+.012,y),(x,y+.010)],.898,.901,'PoolIvory')
    for x in (-1.285,1.285):
        rounded_box('Body',(x,0,.847),(.15,1.03,.10),'Wood',.017,6)
        rounded_box('Body',(x*.946,0,.843),(.076,1.015,.074),'Felt',.016,6)
        for y in (-.36,0,.36):prism('Body',[(x-.010,y),(x,y-.012),(x+.010,y),(x,y+.012)],.898,.901,'PoolIvory')
    for x,y in ((-1.2,-.66),(0,-.69),(1.2,-.66),(-1.2,.66),(0,.69),(1.2,.66)):
        # Lip and lower basket leave the pocket mouth open.
        detail.ring((x,y,.828),(0,0,1),.090,.062,.018,'Rubber',64,'Body')
        for j in range(16):
            a=j*math.tau/16
            detail.tube('Body',[(x+.059*math.cos(a),y+.059*math.sin(a),.82),(x+.045*math.cos(a+.15),y+.045*math.sin(a+.15),.66)],.002,'CueGrip',12)
        for zz,r in ((.69,.048),(.75,.053)):detail.ring((x,y,zz),(0,0,1),r+.0015,r-.0015,.004,'CueGrip',48,'Body')
    for i,(x,y) in enumerate(((-.64,-.12),(.34,0),(.39,.032),(.39,-.032),(.446,.063),(.446,0),(.446,-.063))):
        ball((x,y,.853),.0286,('PoolIvory','PoolBlue','PoolRed','Yellow')[i%4])
        cylinder((x,y,.8816),(0,0,1),.007,.0015,'PoolIvory',sides=24)
    # Chalk and accessory rest are supported by the outer rail.
    rounded_box('Body',(.76,-.765,.914),(.028,.028,.024),'CueTip',.002,3)
    for y in (-.742,.742):box('Body',(0,y,.513),(1.70,.010,.13),'Wood')
    collider((0,0,.57),(2.83,1.66,.62))
    for x in (-.99,.99):collider((x,0,.25),(.26,1.24,.50))

def television_v4():
    # 3.4m-wide modern 16:9 panel, narrow bezel, flush rear mounting plate.
    rounded_box('Body',(0,0,.97),(3.40,.072,1.9125),'Rubber',.014,6)
    rounded_box('Body',(0,-.041,.972),(3.354,.006,1.866),'TVGlass',.006,5)
    rounded_box('Body',(0,.052,.97),(1.02,.036,.37),'PaintedSteel',.012,5)
    box('Body',(0,.082,.97),(.82,.024,.28),'BareSteel')
    for x in (-.36,.36):
        for z in (.89,1.05):detail.fastener((x,.098,z),(0,1,0),.006,'Body')
    for x in (-1.2,-.7,.7,1.2):box('Body',(x,.041,.17),(.30,.010,.015),'BareSteel')
    cylinder((1.47,-.043,.037),(0,1,0),.004,.007,'PoolBlue',sides=24)
    # Soundbar and an anchored cable duct complete the installation.
    rounded_box('Body',(0,-.024,-.09),(1.68,.09,.085),'Rubber',.022,7)
    for i in range(40):box('Body',(-.77+i*.039,-.071,-.09),(.010,.003,.047),'BareSteel')
    box('Body',(0,.082,.31),(.035,.023,.59),'Rubber')
    collider((0,0,.97),(3.40,.11,1.92))

def water_dispenser_v4():
    rounded_box('Body',(0,0,.56),(.42,.43,1.10),'Ceramic',.029,7)
    for x in (-.17,.17):
        for y in (-.16,.16):rounded_box('Body',(x,y,.02),(.058,.065,.04),'Rubber',.009,4)
    rounded_box('Body',(0,-.220,.64),(.31,.018,.35),'Rubber',.013,5)
    for x in (-.077,.077):
        cylinder((x,-.252,.79),(0,1,0),.017,.062,'BareSteel',sides=40)
        detail.tube('Body',[(x,-.275,.79),(x,-.284,.757)],.012,'Ceramic',24)
        rounded_box('Body',(x,-.257,.832),(.027,.047,.035),'BookRed' if x<0 else 'PoolBlue',.006,5)
    rounded_box('Body',(0,-.257,.472),(.33,.12,.029),'Rubber',.009,4)
    for i in range(12):box('Body',(-.137+i*.025,-.262,.489),(.011,.084,.003),'BareSteel')
    for z in (.90,.95,.99):
        cylinder((.115,-.222,z),(0,1,0),.005,.006,'PoolBlue' if z==.95 else 'Rubber',sides=24)
    for z in (.25,.29,.33):box('Body',(0,.219,z),(.28,.004,.013),'Rubber')
    detail.ring((0,0,1.115),(0,0,1),.082,.043,.037,'Rubber',64,'Body')
    # Inverted 19L jug: neck goes into dispenser, shoulder rounds into ribbed body.
    lathe((0,0,1.115),[(0,.037),(.055,.038),(.075,.055),(.100,.087),(.135,.125),(.170,.158),
        (.195,.170),(.230,.173),(.40,.172),(.46,.168),(.49,.155),(.505,.122),(.51,.03)],'JugPlastic',96)
    for zz in (1.35,1.40,1.48,1.55):detail.ring((0,0,zz),(0,0,1),.177,.171,.016,'JugPlastic',96,'Body')
    # Water fill stays inside the closed translucent shell, below the visible air gap.
    lathe((0,0,1.12),[(0,.027),(.055,.030),(.12,.087),(.18,.152),(.39,.159)],'JugWater',72)
    cylinder((0,0,1.16),(0,0,1),.043,.038,'PoolBlue',sides=64)
    box('Body',(0,-.222,.345),(.18,.003,.035),'BookBlue')
    collider((0,-.015,.57),(.43,.50,1.14));collider((0,0,1.39),(.35,.35,.49))

def emit(key,fn,nanite=True):
    global G,HULLS
    G={};HULLS=[];fn();name='SM_Staff_'+key+'_V4'
    export_mesh(name,merge_groups(),kind='Body',hulls=HULLS,collision=bool(HULLS),nanite=nanite)
    records[-1]['asset']=BASE+'/Meshes/'+name;prototypes[key]=name
    bpy.data.objects[name].location=(-12+len(records)%7*4,-50-len(records)//7*4,0)

for i in range(4):emit('BunkBedMessy'+str(i),lambda i=i:bed_v4(i))
for key,fn in dict(Mirror=mirror_v4,WashBasin=basin_v3,BookcaseBody=bookcase_v4,BookshelfBody=bookshelf_v4,
    BookshelfDrawer=shelf_drawer_v4,BilliardTable=billiard_v4,CueRack=cue_rack_v4,Television=television_v4,WaterDispenser=water_dispenser_v4).items():
    emit(key,fn,nanite=key not in ('Mirror','WaterDispenser'))

def bound_carpet(rid,segments):
    global G,HULLS
    G={};HULLS=[]
    for (ax,ay),(bx,by),nx,ny in segments:
        length=math.hypot(bx-ax,by-ay);sx=max(8,int(length/.07));width=.16;pts=[];uvs=[]
        for i in range(sx+1):
            t=i/sx
            # Two restrained lifted spots on each transition; maximum rise 18mm.
            rise=.003+.015*math.exp(-((t-.18)/.10)**2)+.008*math.exp(-((t-.76)/.07)**2)
            for j in range(9):
                v=j/8;d=width*v
                pts.append((ax+(bx-ax)*t+nx*d,ay+(by-ay)*t+ny*d,.004+rise*(1-v)**2))
                uvs.append((t*length/2,d/2))
        surface_solid(pts,sx,8,uvs,'Carpet',.005)
        path=[pts[i*9] for i in range(sx+1)]
        detail.tube('Body',path,.004,'CarpetBinding',12)
        # Closely spaced binding stitches follow the curled boundary.
        for i in range(0,sx+1,2):
            x,y,z=path[i];detail.tube('Body',[(x+nx*.004,y+ny*.004,z+.003),(x+nx*.014,y+ny*.014,z+.001)],.0008,'CarpetBinding',8)
    name='SM_Staff_'+rid+'_CarpetEdges_V4'
    export_mesh(name,merge_groups(),room_id=rid,kind='CarpetEdges',collision=False,nanite=True)
    records[-1]['asset']=BASE+'/Meshes/'+name

# Raised binding at room door thresholds and at the actual material transitions.
bound_carpet('StaffDormitory',[((-16,-2),(-16,2),1,0),((16,-2),(16,2),-1,0)]+
    [((cx-.69,side*1.84),(cx+.69,side*1.84),0,-side) for side in (-1,1) for cx in (-9.5,-.5,9)])
bound_carpet('StaffRecreation',[((-17,-8),(-17,-4),1,0),((17,-8),(17,-4),-1,0),
    ((-14,5.90),(-4,5.90),0,-1),((-3.5,6.02),(8.5,6.02),0,-1)])
bound_carpet('Link',[((0,-2),(0,2),1,0),((4,-2),(4,2),-1,0)])

cfg=copy.deepcopy(CFG);layouts,poses,beds=make_layouts(cfg)
dorm=next(r for r in cfg['rooms'] if r['id']=='StaffDormitory');byid={p['id']:p for p in dorm['furniture']}
for p in poses:
    byid[p['id']].update({k:p[k] for k in ('position','yaw_blender_deg')})
for p in beds:byid[p['id']].update(position=p['position'],yaw_blender_deg=p['yaw_blender_deg'])
wet=next(r for r in cfg['rooms'] if r['id']=='StaffChangingShowers')
for p in wet['furniture']:
    if p['prototype'] in ('WashBasin','Mirror'):
        i=int(p['id'].rsplit('_',1)[1]);p['position'][0]=(-5.4,-2.4,2.4,5.4)[i]
        p['position'][1]=2.207 if p['prototype']=='WashBasin' else 2.040
        p['yaw_blender_deg']=180
rec=next(r for r in cfg['rooms'] if r['id']=='StaffRecreation')
for p in rec['furniture']:
    if p['prototype']=='Sofa':p['position'][1]=7.24;p['yaw_blender_deg']=180
    elif p['prototype']=='CoffeeTable':p['position'][1]=9.04
    elif p['prototype']=='Television':p['position']=[-8.7,11.74,1.12]
    elif p['prototype']=='CueRack':p['position']=[-14.762,-1.1,0]
    elif p['prototype']=='BilliardTable':p['position']=[-8.8,-.25,0]
additional=[dict(id='BilliardB',prototype='BilliardTable',position=[-4.1,-.25,0],yaw_blender_deg=0),
    dict(id='CueRackB',prototype='CueRack',position=[-14.762,1.35,0],yaw_blender_deg=90),
    dict(id='CueRackC',prototype='CueRack',position=[-14.762,3.80,0],yaw_blender_deg=90)]
existing={p['id'] for p in rec['furniture']};rec['furniture'].extend(p for p in additional if p['id'] not in existing)
cfg.update(scene_polish_revision=4,dormitory_layout_revision=4,revision='staff_scene_polish_v4_20261002',
    current_authored_source='ScenePolishV4/Authored/StaffLivingTheme_ScenePolishV4.blend')

# Carry every untouched architectural object and every movable container hinge.
previous=ROOT/CFG['current_authored_source']
with bpy.data.libraries.load(str(previous),link=False) as (src,dst):dst.objects=list(src.objects)
for ob in dst.objects:
    if ob:bpy.context.scene.collection.objects.link(ob)
for room,offset in zip(cfg['rooms'],cfg['preview_placements_m']):
    for p in room['furniture']:
        stem=room['id']+'_'+p['id'];name=stem+('_Body' if p['prototype'] in ('Locker','LockerOpen','Bookcase','Bookshelf','Bedside') else '')
        obj=bpy.data.objects.get(name)
        if not obj:
            source=bpy.data.objects[prototypes[p['prototype']]];obj=source.copy();obj.data=source.data
            obj.name=name;bpy.context.scene.collection.objects.link(obj)
        key=dict(Bookcase='BookcaseBody',Bookshelf='BookshelfBody').get(p['prototype'],p['prototype'])
        if key in prototypes:obj.data=bpy.data.objects[prototypes[key]].data
        obj.location=Vector(offset)+Vector(p['position']);obj.rotation_euler.z=math.radians(p['yaw_blender_deg'])
        hinge=bpy.data.objects.get(stem+'_Hinge')
        if hinge:
            pivot=(-.439,-.215,0) if p['prototype']=='Bookcase' else (-.29,-.284,0) if p['prototype']=='Locker' else (0,0,0)
            hinge.location=obj.location+obj.rotation_euler.to_matrix()@Vector(pivot);hinge.rotation_euler=obj.rotation_euler.copy()
            door=bpy.data.objects.get(stem+'_Door')
            if door and p['prototype']=='Bookshelf':door.data=bpy.data.objects[prototypes['BookshelfDrawer']].data
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'StaffLivingTheme_ScenePolishV4.blend'))
(OUT/'room-polished.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf8')
(OUT/'manifest.json').write_text(json.dumps(dict(objects=records,prototypes=prototypes,layouts=layouts,
    preview_placements=poses,bed_placements=beds,revision=4,tests_run=False,rendered=False),ensure_ascii=False,indent=2),encoding='utf8')
print('STAFF_SCENE_POLISH_V4_AUTHORED',len(records),flush=True)
