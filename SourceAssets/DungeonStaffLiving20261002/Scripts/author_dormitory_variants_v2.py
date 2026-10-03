"""Author three detailed searchable furniture types and the complete dormitory source."""
from pathlib import Path
SCRIPT=Path(__file__).resolve().parent
import json
if json.loads((SCRIPT.parent/'Config/room.json').read_text('utf8')).get('container_open_parts_revision',0)>=3:
    current=SCRIPT/'author_container_open_parts_v3.py'
    exec(compile(current.read_text('utf8'),str(current),'exec'))
    raise SystemExit(0)
_STAFF_REFINEMENT_HELPERS=True
entry=SCRIPT/'author_living.py';code=entry.read_text('utf8')
exec(compile(code.split('for key,fn in PROTOTYPES.items():')[0],str(entry),'exec'))
from dormitory_layout_variants import make_layouts
OUT=ROOT/'DormitoryVariantsV2/Authored';OUT.mkdir(parents=True,exist_ok=True)
BASE=CFG['ue_base']+'/DormitoryVariantsV2';records=[]
for key in ('BookPaper','BookGreen','BookBlue','BookRed'):
    MAPPING[key]=BASE+'/Materials/M_Dorm_'+key;MATS[key]=bpy.data.materials.new('RS_'+key)

def solid(c,size,mat='Wood'):
    rounded_box('Body',c,size,mat,.004,3);collider(c,size)

def books(x0,y,z,count,seed):
    import random
    rr=random.Random(seed);x=x0
    for i in range(count):
        thickness=rr.uniform(.025,.043);height=rr.uniform(.195,.265);depth=rr.uniform(.12,.17)
        color=('BookGreen','BookBlue','BookRed')[rr.randrange(3)]
        # Separate bound covers, spine and page block, plus embossed spine bands.
        rounded_box('Body',(x+thickness/2,y,z+height/2),(thickness-.005,depth-.014,height-.012),'BookPaper',.0015,2)
        for side in (-1,1):
            rounded_box('Body',(x+thickness/2+side*(thickness/2-.0015),y,z+height/2),(.003,depth,height),color,.001,2)
        rounded_box('Body',(x+thickness/2,y-depth/2+.002,z+height/2),(thickness,.004,height),color,.001,2)
        for zz in (.04,height-.035):box('Body',(x+thickness/2,y-depth/2-.0005,z+zz),(thickness*.78,.002,.004),'BookPaper')
        for page in range(4):box('Body',(x+thickness/2,y+depth/2-.005,z+.04+page*(height-.08)/4),(thickness-.006,.0015,.001),'Fabric')
        x+=thickness+rr.uniform(.004,.010)
    # Horizontally piled spare manuals, placed on the same actual shelf.
    for i in range(2):
        rounded_box('Body',(x+.13,y,z+.014+i*.022),(.23,.155,.019),'BookPaper',.002,3)
        for zz in (-.009,.009):box('Body',(x+.13,y,z+.014+i*.022+zz),(.24,.165,.002),'BookBlue' if i else 'BookRed')

def emit(name):
    export_mesh(name,merge_groups(),kind='Body',hulls=HULLS)
    records[-1]['asset']=BASE+'/Meshes/'+name
    bpy.data.objects[name].location=(-12+len(records)*3,-44,0)
    return bpy.data.objects[name]

# 96 x 40 x 198cm bookcase: framed upper shelving and a real lower cabinet.
G={};HULLS=[]
for x in (-.465,.465):solid((x,0,1.0),(.03,.40,1.94),'OlivePaint')
solid((0,.185,1.0),(.90,.03,1.94),'OlivePaint')
for z in (.11,.82,1.20,1.57,1.96):solid((0,0,z),(.96,.40,.035))
for x in (-.37,.37):solid((x,0,.052),(.065,.32,.105),'PaintedSteel')
for i,z in enumerate((.84,1.22,1.59)):books(-.405,-.015,z,9-i*2,41+i)
for z in (.26,.68):cylinder((-.439,-.215,z),(0,0,1),.010,.067,'BareSteel')
bookcase=emit('SM_Dorm_BookcaseBody_V2')
G={};HULLS=[]
solid((.434,0,.461),(.868,.030,.654))
rounded_box('Body',(.434,-.019,.461),(.738,.014,.528),'Wood',.008,4)
for xx in (.058,.810):box('Body',(xx,-.029,.461),(.023,.009,.60),'OlivePaint')
for z in (.172,.750):box('Body',(.434,-.029,z),(.77,.009,.024),'OlivePaint')
detail.tube('Body',[(.775,-.024,.40),(.775,-.055,.40),(.775,-.055,.53),(.775,-.024,.53)],.006,'BareSteel',16)
bookdoor=emit('SM_Dorm_BookcaseDoor_V2')

# 88 x 34 x 184cm open shelf: metal corner uprights, wood shelves and books.
G={};HULLS=[]
for x in (-.405,.405):
    for y in (-.145,.145):solid((x,y,.92),(.028,.028,1.84),'PaintedSteel')
for z in (.14,.56,.98,1.40,1.81):
    solid((0,0,z),(.88,.34,.028))
    solid((0,.15,z-.037),(.81,.026,.046),'OlivePaint')
for i,z in enumerate((.158,.578,.998,1.418)):books(-.34,-.005,z,5+i%3,63+i)
detail.tube('Body',[(-.40,.158,.19),(.40,.158,1.75)],.006,'BareSteel',12)
detail.tube('Body',[(.40,.158,.19),(-.40,.158,1.75)],.006,'BareSteel',12)
bookshelf=emit('SM_Dorm_Bookshelf_V2')

# 52 x 42 x 64cm bedside cabinet: supported top, open lower shelf and pull drawer.
G={};HULLS=[]
solid((0,0,.618),(.52,.42,.044))
solid((0,.196,.39),(.48,.025,.39))
for x in (-.247,.247):solid((x,0,.39),(.026,.42,.41))
for z in (.19,.325,.56):solid((0,0,z),(.48,.40,.018))
for x in (-.215,.215):
    for y in (-.165,.165):
        solid((x,y,.096),(.03,.03,.19),'PaintedSteel')
        rounded_box('Body',(x,y,.010),(.046,.046,.020),'Rubber',.004,3)
bedside=emit('SM_Dorm_BedsideBody_V2')
G={};HULLS=[]
solid((0,-.228,.445),(.478,.028,.198))
for x in (-.221,.221):solid((x,-.04,.432),(.018,.36,.146))
solid((0,.131,.432),(.444,.019,.146));solid((0,-.04,.367),(.444,.36,.016))
detail.tube('Body',[(-.073,-.246,.444),(-.073,-.272,.444),(.073,-.272,.444),(.073,-.246,.444)],.006,'BareSteel',16)
drawer=emit('SM_Dorm_BedsideDrawer_V2')

layout,previews,containers=make_layouts(CFG)
with bpy.data.libraries.load(str(ROOT/'SearchContainersV1/Authored/StaffLivingTheme_SearchContainersV1.blend'),link=False) as (src,dst):
    dst.objects=[n for n in src.objects if not any(n.startswith('StaffDormitory_'+key) for key in ('Desk_','Chair_','Locker_','Bookcase_','Bookshelf_','Bedside'))]
for obj in dst.objects:
    if obj:bpy.context.scene.collection.objects.link(obj)
prototypes={k:bpy.data.objects[v] for k,v in dict(Bookcase='SM_Dorm_BookcaseBody_V2',Bookshelf='SM_Dorm_Bookshelf_V2',Bedside='SM_Dorm_BedsideBody_V2',
    Desk='SM_Staff_Desk',Chair='SM_Staff_Chair',Locker='SM_Staff_SearchLockerBody_V1').items()}
motions=dict(Bookcase=('SM_Dorm_BookcaseDoor_V2',(-.439,-.215,0),'Swing'),Bedside=('SM_Dorm_BedsideDrawer_V2',(0,0,0),'Drawer'),
    Locker=('SM_Staff_SearchLockerDoor_V1',(-.29,-.284,0),'Swing'))
for p in previews:
    searchable=p['prototype'] not in ('Desk','Chair')
    source=prototypes[p['prototype']];obj=source.copy();obj.data=source.data
    name='StaffDormitory_'+p['id'];obj.name=name+('_Body' if searchable else '')
    bpy.context.scene.collection.objects.link(obj);obj.location=p['position'];obj.rotation_euler.z=math.radians(p['yaw_blender_deg'])
    if p['prototype'] in motions:
        moving,pivot,motion=motions[p['prototype']]
        hinge=bpy.data.objects.new(name+'_Hinge',None);bpy.context.scene.collection.objects.link(hinge)
        hinge.location=obj.location+obj.rotation_euler.to_matrix()@Vector(pivot);hinge.rotation_euler=obj.rotation_euler.copy()
        d=bpy.data.objects[moving].copy();d.data=bpy.data.objects[moving].data;d.name=name+'_Door'
        bpy.context.scene.collection.objects.link(d);d.parent=hinge;d.location=(0,0,0);d.rotation_euler=(0,0,0)
paths={r['name']:r['asset'] for r in records}
specs=dict(Bookcase=dict(body=paths['SM_Dorm_BookcaseBody_V2'],door=paths['SM_Dorm_BookcaseDoor_V2'],hinge_cm=[-43.9,21.5,0],motion='Swing',caption='员工书柜'),
    Bookshelf=dict(body=paths['SM_Dorm_Bookshelf_V2'],door=None,hinge_cm=[0,0,0],motion='OpenShelf',caption='员工书架'),
    Bedside=dict(body=paths['SM_Dorm_BedsideBody_V2'],door=paths['SM_Dorm_BedsideDrawer_V2'],hinge_cm=[0,0,0],motion='Drawer',caption='床头柜'))
for p in containers:p.update(specs[p['prototype']])
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'StaffLivingTheme_DormitoryVariantsV2.blend'))
(OUT/'manifest.json').write_text(json.dumps(dict(objects=records,containers=containers,preview_placements=previews,
    layouts=layout,tests_run=False,rendered=False,rewards_deferred=True,source_units='metres; UE centimetres'),ensure_ascii=False,indent=2),encoding='utf8')
(OUT/'layouts.json').write_text(json.dumps(layout,ensure_ascii=False,indent=2),encoding='utf8')
print('STAFF_DORM_VARIANTS_AUTHORED',len(records),len(containers),flush=True)
