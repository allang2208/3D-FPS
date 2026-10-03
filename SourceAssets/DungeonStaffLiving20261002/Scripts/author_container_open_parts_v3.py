"""Give the shelf a real pull-out storage box; preserve the complete V2 room source."""
from pathlib import Path
SCRIPT=Path(__file__).resolve().parent
import json
if json.loads((SCRIPT.parent/'Config/room.json').read_text('utf8')).get('scene_polish_revision',0)>=4:
    current=SCRIPT/'author_scene_polish_v4.py'
    exec(compile(current.read_text('utf8'),str(current),'exec'))
    raise SystemExit(0)
_STAFF_REFINEMENT_HELPERS=True
entry=SCRIPT/'author_living.py';code=entry.read_text('utf8')
exec(compile(code.split('for key,fn in PROTOTYPES.items():')[0],str(entry),'exec'))
OUT=ROOT/'ContainerOpenPartsV3/Authored';OUT.mkdir(parents=True,exist_ok=True)
BASE=CFG['ue_base']+'/ContainerOpenPartsV3';records=[]
for key in ('BookPaper','BookGreen','BookBlue','BookRed'):
    MAPPING[key]=CFG['ue_base']+'/DormitoryVariantsV2/Materials/M_Dorm_'+key
    MATS[key]=bpy.data.materials.new('RS_'+key)
v2=SCRIPT/'author_dormitory_variants_v2.py';old=v2.read_text('utf8')
exec(compile(old[old.index('def solid(c,size'):old.index('# 96 x 40')],str(v2),'exec'))

# Keep the upper shelf silhouette and books. The lowest bay is now a drawer;
# fixed runner rails and open spaces remain part of the stationary frame.
G={};HULLS=[]
for x in (-.405,.405):
    for y in (-.145,.145):solid((x,y,.92),(.028,.028,1.84),'PaintedSteel')
for z in (.14,.56,.98,1.40,1.81):
    solid((0,0,z),(.88,.34,.028))
    solid((0,.15,z-.037),(.81,.026,.046),'OlivePaint')
for i,z in enumerate((.578,.998,1.418)):books(-.34,-.005,z,5+i%3,64+i)
for x in (-.385,.385):
    solid((x,-.004,.198),(.012,.27,.024),'BareSteel')
    for y in (-.095,.095):cylinder((x,y,.205),(1,0,0),.011,.021,'BareSteel',sides=16)
detail.tube('Body',[(-.40,.158,.19),(.40,.158,1.75)],.006,'BareSteel',12)
detail.tube('Body',[(.40,.158,.19),(-.40,.158,1.75)],.006,'BareSteel',12)
body=emit('SM_Dorm_BookshelfBody_V3')

# Closed box fits between the uprights and beneath the second shelf; its origin
# stays at the shelf base, so a local forward translation exposes the cavity.
G={};HULLS=[]
solid((0,-.177,.338),(.784,.024,.322))
rounded_box('Body',(0,-.192,.338),(.660,.012,.244),'Wood',.009,4)
for x in (-.364,.364):solid((x,-.020,.324),(.020,.288,.282))
solid((0,.123,.324),(.728,.018,.282))
solid((0,-.020,.174),(.728,.288,.018))
for x in (-.374,.374):solid((x,-.004,.199),(.008,.26,.018),'BareSteel')
detail.tube('Body',[(-.085,-.201,.338),(-.085,-.231,.338),(.085,-.231,.338),(.085,-.201,.338)],.007,'BareSteel',18)
for x in (-.085,.085):cylinder((x,-.201,.338),(0,1,0),.013,.008,'BareSteel',sides=20)
books(-.30,-.028,.184,4,93)
drawer=emit('SM_Dorm_BookshelfStorageBox_V3')

previous=ROOT/'DormitoryVariantsV2/Authored/StaffLivingTheme_DormitoryVariantsV2.blend'
with bpy.data.libraries.load(str(previous),link=False) as (src,dst):
    dst.objects=[n for n in src.objects if 'SM_Dorm_Bookshelf_V2' not in n and not n.startswith('StaffDormitory_Bookshelf_')]
for obj in dst.objects:
    if obj:bpy.context.scene.collection.objects.link(obj)
previous_manifest=json.loads((ROOT/'DormitoryVariantsV2/Authored/manifest.json').read_text('utf8'))
containers=[]
for p in previous_manifest['preview_placements']:
    if p['prototype']!='Bookshelf':continue
    name='StaffDormitory_'+p['id'];b=body.copy();b.data=body.data;b.name=name+'_Body'
    bpy.context.scene.collection.objects.link(b);b.location=p['position'];b.rotation_euler.z=math.radians(p['yaw_blender_deg'])
    hinge=bpy.data.objects.new(name+'_Hinge',None);bpy.context.scene.collection.objects.link(hinge)
    hinge.location=b.location;hinge.rotation_euler=b.rotation_euler.copy()
    d=drawer.copy();d.data=drawer.data;d.name=name+'_Door';bpy.context.scene.collection.objects.link(d)
    d.parent=hinge;d.location=(0,0,0);d.rotation_euler=(0,0,0)
    containers.append(dict(id=p['id'],container_id='StaffDormitory.'+p['id'],body=records[0]['asset'],door=records[1]['asset'],
        hinge_cm=[0,0,0],motion='Drawer',drawer_travel_cm=[0,32,0]))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'StaffLivingTheme_ContainerOpenPartsV3.blend'))
(OUT/'manifest.json').write_text(json.dumps(dict(objects=records,containers=containers,
    revision=3,all_containers_require_moving_part=True,tests_run=False,rendered=False),ensure_ascii=False,indent=2),encoding='utf8')
print('STAFF_CONTAINER_OPEN_PARTS_AUTHORED',len(records),len(containers),flush=True)
