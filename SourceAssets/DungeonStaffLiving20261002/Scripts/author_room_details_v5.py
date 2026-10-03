"""Dimensioned bathroom, refreshment containers and supported cloth assemblies."""
from pathlib import Path
SCRIPT=Path(__file__).resolve().parent
import json
if json.loads((SCRIPT.parent/'Config/room.json').read_text('utf8')).get('wall_inset_revision',0)>=6:
    current=SCRIPT/'author_wall_inset_v6.py'
    exec(compile(current.read_text('utf8'),str(current),'exec'))
    raise SystemExit(0)
_STAFF_REFINEMENT_HELPERS=True
entry=SCRIPT/'author_living.py'
exec(compile(entry.read_text('utf8').split('for key,fn in PROTOTYPES.items():')[0],str(entry),'exec'))
import random,copy
OUT=ROOT/'RoomDetailsV5/Authored';OUT.mkdir(parents=True,exist_ok=True)
BASE=CFG['ue_base']+'/RoomDetailsV5';records=[];prototypes={}
for key in ('Linen','Terry','Hem','Carpet'):
    MAPPING[key]=CFG['ue_base']+'/RefinementV3/Materials/'+('MI_Staff_NavyCarpet_V3' if key=='Carpet' else 'M_Staff_'+key+'_V3')
    MATS[key]=bpy.data.materials.new('RS_'+key)
for key in ('BookPaper','BookGreen','BookBlue','BookRed'):
    MAPPING[key]=CFG['ue_base']+'/DormitoryVariantsV2/Materials/M_Dorm_'+key;MATS[key]=bpy.data.materials.new('RS_'+key)
for key in ('JugPlastic','JugWater','CueMaple','CueGrip','CueTip','PoolIvory','PoolBlue','PoolRed','TVGlass','CarpetBinding'):
    MAPPING[key]=CFG['ue_base']+'/ScenePolishV4/Materials/M_Staff_'+key+'_V4';MATS[key]=bpy.data.materials.new('RS_'+key)
for key in ('PaddleRed','PaddleBlack','FreshPlastic','Coffee','ToiletSign'):
    MAPPING[key]=BASE+'/Materials/M_Staff_'+key+'_V5';MATS[key]=bpy.data.materials.new('RS_'+key)
MAPPING['Felt']=BASE+'/Materials/MI_Staff_BaizeRelief_V5'
v4=SCRIPT/'author_scene_polish_v4.py';code=v4.read_text('utf8')
exec(compile(code[code.index('v3=SCRIPT/'):code.index('def emit(')],str(v4),'exec'))

def water_v5():
    water_dispenser_v4()
    # Remove the decorative blue cap. The bottle neck actually enters the
    # socket; a hollow seal is flush with the machine rather than perched on it.
    for g in G.values():
        keep=[]
        for i,f in enumerate(g['f']):
            p=[g['v'][j] for j in f];zs=[q[2] for q in p]
            if g['m'][i]=='PoolBlue' and min(zs)>1.13:continue
            if g['m'][i]=='Rubber' and min(zs)>1.09:continue
            keep.append(i)
        for field in ('f','m','uv','smooth'):g[field]=[g[field][i] for i in keep]
    # Lower the whole jug and its internal water by 4cm into the receiving well.
    for g in G.values():
        ids={j for f,m in zip(g['f'],g['m']) if m in ('JugPlastic','JugWater') for j in f}
        for j in ids:
            x,y,z=g['v'][j];g['v'][j]=(x,y,z-.04)
    detail.ring((0,0,1.102),(0,0,1),.067,.040,.019,'FreshPlastic',72,'Body')
    detail.ring((0,0,1.103),(0,0,1),.043,.037,.012,'Rubber',64,'Body')
    for x in (-.10,.10):box('Body',(x,0,1.106),(.047,.08,.009),'Ceramic')

def laundry_v5():
    # Retain the basket, strip its obsolete placeholders and add a real floor.
    laundry();remove_fabric()
    for i in range(9):box('Body',(-.30+i*.075,0,.079),(.012,.54,.015),'BareSteel')
    for y in (-.23,0,.23):box('Body',(0,y,.077),(.65,.012,.018),'BareSteel')
    # Every layer shares the same low-amplitude supported surface. No corner
    # rotates outside the 65x53cm internal footprint, and no layer floats.
    nx,ny=32,28;top=.095
    for layer in range(10):
        pts=[];uvs=[];length=.57-(layer%3)*.012;width=.45-(layer%2)*.018
        cx=.006*math.sin(layer*1.7);cy=.007*math.cos(layer*.9)
        thick=.047 if layer<8 else .041
        for i in range(nx+1):
            u=i/nx;x=(u-.5)*length
            for j in range(ny+1):
                v=j/ny;y=(v-.5)*width
                wrinkle=.006*math.sin((x+cx)*24+(y+cy)*20)+.003*math.sin((y+cy)*37)
                # The underside of this towel meets the previous layer's top.
                z=top+thick+wrinkle
                pts.append((x+cx,y+cy,z));uvs.append((x/.35,y/.35))
        boundary=surface_solid(pts,nx,ny,uvs,'Terry',thick);sewn_hem(pts,boundary,radius=.0015)
        top+=thick-.001
    # Looser top fold remains within the rim and rests on the last towel.
    pts=[];uvs=[]
    for i in range(nx+1):
        u=i/nx;x=(u-.5)*.52
        for j in range(ny+1):
            v=j/ny;y=(v-.5)*.40
            fold=.040*math.sin(math.pi*u)**2*math.sin(v*math.pi)**2
            wrinkle=.006*math.sin((x-.014)*24+(y+.012)*20)+.003*math.sin((y+.012)*37)
            pts.append((x-.014,y+.012,top+.025+fold+wrinkle));uvs.append((x/.35,y/.35))
    boundary=surface_solid(pts,nx,ny,uvs,'Terry',.025);sewn_hem(pts,boundary,radius=.0015)

def paddle():
    # Rounded oval with five wood laminations, distinct rubber and a shaped grip.
    shape=[(.080*math.cos(a),.025+.094*math.sin(a)) for a in [i*math.tau/96 for i in range(96)]]
    prism('Body',shape,.002,.008,'CueMaple')
    prism('Body',[(x*.981,(y-.025)*.981+.025) for x,y in shape],.008,.010,'PaddleRed')
    prism('Body',[(x*.981,(y-.025)*.981+.025) for x,y in shape],0,.002,'PaddleBlack')
    for zz in (.0033,.0047,.0061):
        detail.tube('Body',[(x,y,zz) for x,y in shape]+[(shape[0][0],shape[0][1],zz)],.00035,'BookPaper',8)
    grip=[(-.014,-.039),(-.018,-.082),(-.016,-.145),(-.009,-.153),(.009,-.153),(.016,-.145),(.018,-.082),(.014,-.039)]
    prism('Body',grip,.0005,.012,'CueMaple')
    for side in (-1,1):
        path=[(side*.012,-.075,.012),(side*.012,-.141,.012)]
        detail.tube('Body',path,.0022,'BookRed',12)
    rounded_box('Body',(0,-.116,.013),(.013,.038,.002),'BookPaper',.002,4)

def countertop():
    rounded_box('Body',(0,0,.93),(3.60,.75,.06),'Ceramic',.017,7)
    for x in (-1.52,0,1.52):
        beam('Body',(x,.22,.90),(x,.22,.10),.045,.045,'BareSteel')
    collider((0,0,.93),(3.60,.75,.06))

def cabinet_body():
    for x in (-.326,.326):solid((x,0,.48),(.018,.65,.79),'OlivePaint')
    solid((0,.313,.48),(.634,.024,.79),'OlivePaint')
    for z in (.10,.48,.876):solid((0,0,z),(.634,.65,.024),'Wood')
    for x in (-.275,.275):
        for y in (-.25,.25):solid((x,y,.055),(.04,.045,.11),'PaintedSteel')
    for z in (.28,.72):cylinder((-.312,-.343,z),(0,0,1),.009,.05,'BareSteel',sides=32)

def cabinet_door():
    solid((.312,0,.489),(.624,.030,.762),'OlivePaint')
    rounded_box('Body',(.312,-.022,.489),(.548,.014,.69),'OlivePaint',.009,5)
    detail.tube('Body',[(.538,-.025,.58),(.538,-.065,.58),(.538,-.065,.69),(.538,-.025,.69)],.007,'BareSteel',20)
    for z in (.58,.69):cylinder((.538,-.027,z),(0,1,0),.012,.016,'BareSteel',sides=28)

def fridge_body(upper):
    z0,z1=(1.045,1.72) if upper else (.065,1.045)
    for x in (-.375,.375):solid((x,0,(z0+z1)/2),(.040,.72,z1-z0),'Ceramic')
    solid((0,.335,(z0+z1)/2),(.71,.050,z1-z0),'Ceramic')
    for z in (z0,z1):solid((0,0,z),(.71,.69,.027),'Ceramic')
    for z in ((1.35,) if upper else (.33,.62,.87)):
        rounded_box('Body',(0,-.01,z),(.68,.61,.014),'PoolIvory',.006,4)
        collider((0,-.01,z),(.68,.61,.018))
    if not upper:
        solid((0,.22,.155),(.66,.16,.21),'Rubber')
        for x in (-.30,.30):
            for y in (-.27,.27):cylinder((x,y,.045),(0,0,1),.026,.09,'Rubber',sides=32)
        for i in range(8):box('Body',(-.29+i*.083,.369,.30),(.020,.014,.34),'BareSteel')
    else:
        rounded_box('Body',(.26,.25,1.09),(.057,.046,.035),'FreshPlastic',.007,4)

def fridge_door(upper):
    z,h=(1.375,.622) if upper else (.553,.948)
    solid((.355,0,z),(.71,.065,h),'Ceramic')
    box('Body',(.355,.038,z),(.652,.012,h-.046),'Rubber')
    rounded_box('Body',(.355,.051,z),(.62,.028,h-.08),'FreshPlastic',.007,4)
    if not upper:
        for zz in (.23,.59):
            rounded_box('Body',(.355,.098,zz),(.56,.089,.036),'FreshPlastic',.008,5)
            box('Body',(.355,.140,zz+.070),(.56,.008,.10),'FreshPlastic')
    for zz in (z-.12,z+.12):cylinder((.623,-.052,zz),(0,1,0),.010,.044,'BareSteel',sides=32)
    detail.tube('Body',[(.623,-.073,z-.12),(.623,-.095,z-.10),(.623,-.095,z+.10),(.623,-.073,z+.12)],.011,'BareSteel',24)

def kettle():
    lathe((0,0,0),[(.022,.071),(.03,.083),(.08,.092),(.17,.085),(.24,.069),(.25,.065)],'BareSteel',96)
    cylinder((0,0,.012),(0,0,1),.080,.024,'Rubber',sides=64)
    detail.ring((0,0,.251),(0,0,1),.070,.022,.015,'BareSteel',64,'Body')
    rounded_box('Body',(0,0,.269),(.035,.037,.024),'Rubber',.008,5)
    # Spout is a hollow flared tube, not a capped cylinder.
    detail.sweep('Body',[(0,-.067,.21),(0,-.110,.218),(0,-.141,.239)],.024,'BareSteel',40,.008)
    detail.ring((0,-.143,.240),(0,-.73,.68),.025,.016,.010,'BareSteel',48,'Body')
    detail.tube('Body',[(0,.064,.23),(0,.133,.23),(0,.154,.204),(0,.154,.092),(0,.127,.065),(0,.081,.072)],.014,'Rubber',32)
    rounded_box('Body',(0,.128,.025),(.025,.042,.016),'BookRed',.004,4)
    for z in (.075,.11,.145,.18):box('Body',(.089,0,z),(.002,.032,.002),'PoolIvory')
    detail.tube('Body',[(.07,.02,.012),(.13,.10,.011),(.16,.18,.011)],.003,'Rubber',12)

def coffee_machine():
    rounded_box('Body',(0,.035,.275),(.43,.33,.52),'BareSteel',.018,7)
    rounded_box('Body',(0,-.112,.343),(.386,.045,.28),'Rubber',.010,5)
    rounded_box('Body',(0,-.03,.554),(.40,.28,.035),'BareSteel',.007,5)
    rounded_box('Body',(0,.168,.23),(.30,.055,.39),'FreshPlastic',.018,6)
    rounded_box('Body',(0,-.18,.03),(.43,.25,.042),'Rubber',.013,6)
    for i in range(14):box('Body',(-.18+i*.027,-.19,.054),(.012,.19,.004),'BareSteel')
    rounded_box('Body',(0,-.139,.422),(.145,.009,.062),'Screen',.004,5)
    for x in (-.129,.129):
        cylinder((x,-.149,.42),(0,1,0),.022,.018,'BareSteel',sides=48)
        cylinder((x,-.160,.42),(0,1,0),.015,.006,'Rubber',sides=40)
    cylinder((0,-.163,.30),(0,0,1),.047,.040,'BareSteel',sides=48)
    detail.tube('Body',[(0,-.18,.30),(0,-.269,.30)],.015,'Rubber',24)
    for x in (-.018,.018):detail.tube('Body',[(x,-.16,.279),(x,-.16,.247)],.004,'BareSteel',20)
    detail.tube('Body',[(.165,-.11,.31),(.20,-.14,.27),(.20,-.21,.15)],.006,'BareSteel',24)
    for x in (-.165,.165):
        for y in (-.1,.14):rounded_box('Body',(x,y,.012),(.035,.046,.024),'Rubber',.006,5)
    # Ceramic mug rests on the tray directly beneath the extraction head.
    lathe((0,-.16,.055),[(0,.032),(.018,.035),(.079,.039),(.079,.031),(.010,.028),(.008,.003)],'Ceramic',64)
    detail.ring((0,-.16,.134),(0,0,1),.040,.031,.006,'Ceramic',64,'Body')
    cylinder((0,-.16,.128),(0,0,1),.030,.002,'Coffee',sides=64)
    path=[(.039+.017*math.sin(a),-.16,.096+.023*math.cos(a)) for a in [i*math.pi/32 for i in range(33)]]
    detail.tube('Body',path,.006,'Ceramic',20)

def toilet():
    # Hollow vitreous-china bowl with oval rim, internal slopes and waste throat.
    rings=[(.29,.40,.18,-.008),(.38,.53,.31,-.05),(.405,.56,.397,-.05),(.365,.510,.414,-.05),
        (.305,.430,.400,-.05),(.250,.350,.318,-.02),(.125,.165,.235,.022)]
    vs=[];fs=[];n=96
    for w,d,z,cy in rings:
        for j in range(n):
            a=j*math.tau/n;vs.append((w/2*math.cos(a),cy+d/2*math.sin(a),z))
    for row in range(len(rings)-1):
        for j in range(n):fs.append((row*n+j,row*n+(j+1)%n,(row+1)*n+(j+1)%n,(row+1)*n+j))
    poly('Body',vs,fs,'Ceramic',smooth=True)
    rounded_box('Body',(0,.045,.106),(.26,.34,.205),'Ceramic',.065,9)
    # Oval open seat follows the bowl contour, with real hinge mounts.
    path=[(.194*math.cos(a),-.05+.269*math.sin(a),.425) for a in [i*math.tau/96 for i in range(97)]]
    detail.tube('Body',path,.013,'FreshPlastic',20)
    for x in (-.095,.095):
        rounded_box('Body',(x,.187,.418),(.04,.066,.019),'FreshPlastic',.005,5)
        cylinder((x,.194,.436),(1,0,0),.009,.053,'BareSteel',sides=32)
    rounded_box('Body',(0,.280,.578),(.395,.170,.38),'Ceramic',.032,8)
    rounded_box('Body',(0,.280,.781),(.405,.185,.037),'Ceramic',.021,7)
    for x in (-.039,.039):cylinder((x,.280,.804),(0,0,1),.025,.010,'BareSteel',sides=48)
    detail.tube('Body',[(-.12,.31,.10),(-.12,.34,.44),(-.12,.29,.45)],.008,'BareSteel',24)
    detail.ring((-.12,.35,.10),(0,1,0),.025,.009,.012,'BareSteel',32,'Body')
    cylinder((0,.034,.228),(0,0,1),.052,.010,'PoolBlue',sides=64)
    for x in (-.11,.11):detail.fastener((x,-.095,.014),(0,0,1),.009,'Body')
    collider((0,.015,.21),(.405,.59,.44));collider((0,.28,.58),(.40,.18,.43))

def bathroom_shell():
    # 4.0 x 3.2m corner facility. Existing east/north room walls are reused.
    for y in (4.64,7.82):
        if y==7.82:continue
        for x,w in ((11.49,1.70),(14.115,1.45)):
            box('Body',(x,y,1.40),(w,.16,2.80),'Concrete');collider((x,y,1.40),(w,.16,2.80))
            box('Body',(x,y+.083,.69),(w,.015,1.38),'Ceramic')
        box('Body',(12.87,y,2.55),(1.05,.16,.50),'Concrete');collider((12.87,y,2.55),(1.05,.16,.50))
    box('Body',(10.65,6.25,1.40),(.16,3.38,2.80),'Concrete');collider((10.65,6.25,1.40),(.16,3.38,2.80))
    box('Body',(10.736,6.25,.69),(.015,3.20,1.38),'Ceramic')
    box('Body',(12.72,6.25,2.865),(4.28,3.38,.13),'Concrete');collider((12.72,6.25,2.865),(4.28,3.38,.13))
    box('Body',(12.76,6.25,.009),(4.08,3.14,.018),'Ceramic')
    # Door jamb and threshold; door stands open into its clear west-side bay.
    for x in (12.34,13.40):box('Body',(x,4.55,1.125),(.053,.070,2.25),'PaintedSteel')
    box('Body',(12.87,4.55,2.247),(1.10,.07,.06),'PaintedSteel')
    box('Body',(12.87,4.64,.013),(1.03,.25,.026),'BareSteel')
    angle=math.radians(88);co,si=math.cos(angle),math.sin(angle)
    doorcenter=(12.37+.50*co,4.55+.50*si,1.11)
    box('Body',doorcenter,(1.00,.045,2.20),'OlivePaint',angle)
    collider(doorcenter,(1.00,.06,2.20),angle)
    handle=(12.37+.88*co,4.55+.88*si,1.03)
    cylinder(handle,(-si,co,0),.022,.10,'BareSteel',sides=40)
    # Cubicle divider and an open stall door leave a 95cm access aisle.
    box('Body',(13.35,7.14,.96),(.040,1.32,1.89),'FreshPlastic');collider((13.35,7.14,.96),(.040,1.32,1.89))
    for y in (6.58,7.70):cylinder((13.35,y,.09),(0,0,1),.024,.18,'BareSteel',sides=32)
    for y in (4.8,7.6):box('Body',(12.76,y,.066),(4.0,.032,.12),'Mortar')
    # Flush plaque with fresh atlas UVs (independent of old signage atlas).
    box('Body',(12.87,4.55,2.51),(.45,.025,.19),'FreshPlastic')
    poly('Body',[(12.65,4.535,2.42),(13.09,4.535,2.42),(13.09,4.535,2.60),(12.65,4.535,2.60)],[(0,1,2,3)],'ToiletSign',[[(0,0),(1,0),(1,1),(0,1)]])
    # Wall toilet-paper holder, accessible beside the bowl.
    detail.tube('Body',[(14.72,7.14,.68),(14.62,7.14,.68),(14.62,6.99,.68)],.008,'BareSteel',24)
    cylinder((14.62,7.085,.68),(0,1,0),.052,.115,'BookPaper',sides=64)

def emit(key,fn,nanite=True):
    global G,HULLS
    G={};HULLS=[];fn();name='SM_Staff_'+key+'_V5'
    export_mesh(name,merge_groups(),kind='Body',hulls=HULLS,collision=bool(HULLS),nanite=nanite)
    records[-1]['asset']=BASE+'/Meshes/'+name;prototypes[key]=name
    bpy.data.objects[name].location=(-12+len(records)%6*4,-66-len(records)//6*4,0)

for key,fn in dict(WaterDispenser=water_v5,LaundryBasket=laundry_v5,TableTennisPaddle=paddle,
    KitchenCounterTop=countertop,CounterCabinetBody=cabinet_body,CounterCabinetDoor=cabinet_door,
    FridgeLowerBody=lambda:fridge_body(False),FridgeUpperBody=lambda:fridge_body(True),
    FridgeLowerDoor=lambda:fridge_door(False),FridgeUpperDoor=lambda:fridge_door(True),
    ElectricKettle=kettle,CoffeeMachine=coffee_machine,Toilet=toilet,BathroomShell=bathroom_shell).items():
    emit(key,fn,nanite=key!='WaterDispenser')

cfg=copy.deepcopy(CFG);removed=[]
for room in cfg['rooms']:
    removed.extend(dict(room_id=room['id'],id=p['id'],prototype=p['prototype']) for p in room['furniture'] if p['prototype']=='PersonalBox')
    room['furniture']=[p for p in room['furniture'] if p['prototype']!='PersonalBox']
rec=next(r for r in cfg['rooms'] if r['id']=='StaffRecreation')
removed.extend(dict(room_id=rec['id'],id=p['id'],prototype=p['prototype']) for p in rec['furniture'] if p['prototype']=='Refrigerator')
rec['furniture']=[p for p in rec['furniture'] if p['prototype']!='Refrigerator']
counter=next(p for p in rec['furniture'] if p['prototype'] in ('KitchenCounter','KitchenCounterTop'));counter['prototype']='KitchenCounterTop'
for p in rec['furniture']:
    if p['prototype']=='WaterDispenser':p['position']=[14.65,1.65,0]
newprops=[dict(id='PaddleA',prototype='TableTennisPaddle',position=[1.86,-.30,.758],yaw_blender_deg=-24),
    dict(id='PaddleB',prototype='TableTennisPaddle',position=[3.52,.27,.758],yaw_blender_deg=151),
    dict(id='CoffeeMachine',prototype='CoffeeMachine',position=[9.52,-11.43,.96],yaw_blender_deg=180),
    dict(id='ElectricKettle',prototype='ElectricKettle',position=[10.82,-11.37,.96],yaw_blender_deg=163),
    dict(id='BathroomShell',prototype='BathroomShell',position=[0,0,0],yaw_blender_deg=0),
    dict(id='Toilet',prototype='Toilet',position=[14.12,7.38,.018],yaw_blender_deg=0),
    dict(id='BathroomSink',prototype='WashBasin',position=[11.75,7.587,.018],yaw_blender_deg=0),
    dict(id='BathroomMirror',prototype='Mirror',position=[11.75,7.754,1.32],yaw_blender_deg=0),
    dict(id='BathroomLamp',prototype='LampFixture',position=[12.20,6.13,2.73],yaw_blender_deg=90)]
new_ids={p['id'] for p in newprops}
rec['furniture']=[p for p in rec['furniture'] if p['id'] not in new_ids]
rec['furniture'].extend(newprops)
containers=[]
for i in range(5):
    containers.append(dict(id='CounterCabinet_'+str(i),prototype='CounterCabinet',position=[10.6-1.34+i*.67,-11.47,0],yaw_blender_deg=180,
        body='CounterCabinetBody',door='CounterCabinetDoor',hinge_cm=[-31.2,34.3,0],caption='茶水台储物柜',random_open=i in (0,2,4)))
for upper in (False,True):
    containers.append(dict(id='FridgeUpper' if upper else 'FridgeLower',prototype='Fridge',position=[13.85,-11.49,0],yaw_blender_deg=180,
        body='FridgeUpperBody' if upper else 'FridgeLowerBody',door='FridgeUpperDoor' if upper else 'FridgeLowerDoor',
        hinge_cm=[-35.5,38.3,0],caption='冰箱冷冻室' if upper else '冰箱冷藏室',random_open=False))
for c in containers:
    c['body']=next(r['asset'] for r in records if r['name']==prototypes[c['body']]);c['door']=next(r['asset'] for r in records if r['name']==prototypes[c['door']])
    c['container_id']='StaffRecreation.'+c['id']
    rec['furniture']=[p for p in rec['furniture'] if p['id']!=c['id']]
    rec['furniture'].append({k:c[k] for k in ('id','prototype','position','yaw_blender_deg')})

# Four bounded chair plans, selected by the existing no-Tick layout controller.
chairs=[p for p in rec['furniture'] if p['prototype']=='Chair'];rng=random.Random(202610025);variants=[]
for v in range(4):
    pp=[]
    for i,p in enumerate(chairs):
        x,y,z=p['position'];dx=rng.uniform(-.12,.12);dy=rng.uniform(-.14,.14)
        if i%4==v:dy+=(.20 if p['yaw_blender_deg']==0 else -.20)
        y=min(y+dy,4.07) if y<4.5 else y+dy
        yaw=p['yaw_blender_deg']+rng.uniform(-17,17)
        pp.append(dict(id=p['id'],position=[x+dx,y,z],yaw_blender_deg=yaw,position_cm=[(x+dx)*100,-y*100,z*100],yaw_ue=-yaw))
    variants.append(dict(id=v,placements=pp))
chair_layout=dict(version=5,seed=-1,rooms=[dict(id='RecreationChairs',variants=variants)])
chair_poses=variants[0]['placements'];byid={p['id']:p for p in rec['furniture']}
for p in chair_poses:byid[p['id']].update(position=p['position'],yaw_blender_deg=p['yaw_blender_deg'])
cfg.update(room_details_revision=5,revision='staff_room_details_v5_20261002',
    current_authored_source='RoomDetailsV5/Authored/StaffLivingTheme_RoomDetailsV5.blend')

with bpy.data.libraries.load(str(ROOT/'ScenePolishV4/Authored/StaffLivingTheme_ScenePolishV4.blend'),link=False) as (src,dst):
    dst.objects=[n for n in src.objects if 'PersonalBox' not in n and not n.startswith('StaffRecreation_Refrigerator')]
for obj in dst.objects:
    if obj:bpy.context.scene.collection.objects.link(obj)
specs={c['id']:c for c in containers};rng=random.Random(202610025)
for room,offset in zip(cfg['rooms'],cfg['preview_placements_m']):
    for p in room['furniture']:
        stem=room['id']+'_'+p['id']
        if p['id'] in specs and room['id']=='StaffRecreation':
            c=specs[p['id']];body=prototypes['CounterCabinetBody'] if p['prototype']=='CounterCabinet' else prototypes['FridgeUpperBody' if p['id']=='FridgeUpper' else 'FridgeLowerBody']
            source=bpy.data.objects[body];obj=source.copy();obj.data=source.data;obj.name=stem+'_Body';bpy.context.scene.collection.objects.link(obj)
            obj.location=Vector(offset)+Vector(p['position']);obj.rotation_euler.z=math.radians(p['yaw_blender_deg'])
            pivot=Vector((c['hinge_cm'][0]/100,-c['hinge_cm'][1]/100,0));hinge=bpy.data.objects.new(stem+'_Hinge',None);bpy.context.scene.collection.objects.link(hinge)
            hinge.location=obj.location+obj.rotation_euler.to_matrix()@pivot;hinge.rotation_euler=obj.rotation_euler.copy()
            dk='CounterCabinetDoor' if p['prototype']=='CounterCabinet' else 'FridgeUpperDoor' if p['id']=='FridgeUpper' else 'FridgeLowerDoor'
            door=bpy.data.objects[prototypes[dk]].copy();door.data=bpy.data.objects[prototypes[dk]].data;door.name=stem+'_Door'
            bpy.context.scene.collection.objects.link(door);door.parent=hinge;door.location=(0,0,0);door.rotation_euler=(0,0,0)
            continue
        obj=bpy.data.objects.get(stem) or bpy.data.objects.get(stem+'_Body')
        if p['prototype'] in prototypes:
            source=bpy.data.objects[prototypes[p['prototype']]]
            if not obj:obj=source.copy();obj.data=source.data;obj.name=stem;bpy.context.scene.collection.objects.link(obj)
            obj.data=source.data
        if not obj and p in newprops:
            shared=dict(WashBasin='SM_Staff_WashBasin_V4',Mirror='SM_Staff_Mirror_V4',LampFixture='SM_Staff_LampFixture')
            source=bpy.data.objects[shared[p['prototype']]];obj=source.copy();obj.data=source.data;obj.name=stem;bpy.context.scene.collection.objects.link(obj)
        if obj:
            obj.location=Vector(offset)+Vector(p['position']);obj.rotation_euler.z=math.radians(p['yaw_blender_deg'])
        if room['id']=='StaffChangingShowers' and p['prototype'] in ('Locker','LockerOpen'):
            hinge=bpy.data.objects.get(stem+'_Hinge')
            if hinge and rng.random()<.32:hinge.rotation_euler.z-=math.radians(rng.uniform(38,78))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'StaffLivingTheme_RoomDetailsV5.blend'))
(OUT/'room-detailed.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf8')
(OUT/'manifest.json').write_text(json.dumps(dict(objects=records,prototypes=prototypes,containers=containers,removed=removed,
    chair_layout=chair_layout,chair_poses=chair_poses,revision=5,tests_run=False,rendered=False),ensure_ascii=False,indent=2),encoding='utf8')
print('STAFF_ROOM_DETAILS_V5_AUTHORED',len(records),flush=True)
