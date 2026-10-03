"""Split the accepted lockers into an authored body and a hinged door.
Background Blender production only; preserve the complete intact-wall source.
"""
from pathlib import Path
SCRIPT=Path(__file__).resolve().parent
_STAFF_REFINEMENT_HELPERS=True
entry=SCRIPT/'author_living.py';code=entry.read_text('utf8')
exec(compile(code.split('for key,fn in PROTOTYPES.items():')[0],str(entry),'exec'))
OUT=ROOT/'SearchContainersV1/Authored';OUT.mkdir(parents=True,exist_ok=True)
BASE=CFG['ue_base']+'/SearchContainersV1'
records=[]

G={};HULLS=[]
def solid(c,size,mat):
    box('Body',c,size,mat);collider(c,size)
for x in (-.32,.32):solid((x,0,.97),(.025,.55,1.94),'OlivePaint')
solid((0,.261,.97),(.60,.025,1.94),'OlivePaint')
for z in (.12,1.915):solid((0,0,z),(.64,.55,.035),'OlivePaint')
for z in (.6,1.35,1.66):solid((0,.02,z),(.58,.50,.019),'BareSteel')
for x in (-.23,.23):solid((x,0,.055),(.07,.45,.11),'PaintedSteel')
for z in (.45,1.58):cylinder((-.29,-.284,z),(0,0,1),.013,.09,'BareSteel')
export_mesh('SM_Staff_SearchLockerBody_V1',merge_groups(),kind='Body',hulls=HULLS)
records[-1]['asset']=BASE+'/Meshes/'+records[-1]['name']
body=bpy.data.objects[records[-1]['name']];body.location=(-5,-36,0)

# Local origin is the real left hinge, not the centre of the panel.
G={};HULLS=[];c=Vector((.29,0,1.05));pivot=Vector((0,0,0));v=Vector((0,1,0))
box('Body',c+Vector((0,0,.27)),(.58,.025,1.25),'OlivePaint')
box('Body',c-Vector((0,0,.58)),(.58,.025,.36),'OlivePaint')
for i in range(5):
    z=.59+i*.045
    beam('Body',(.025,0,z),(.555,0,z),.025,.025,'OlivePaint')
for side in (-1,1):box('Body',c+Vector((side*.282,0,0)),(.018,.045,1.83),'OlivePaint')
handle=Vector((.52,-.039,1.05))
detail.tube('Body',[handle-Vector((0,0,.07)),handle-v*.018-Vector((0,0,.07)),
    handle-v*.018+Vector((0,0,.07)),handle+Vector((0,0,.07))],.007,'BareSteel',16)
cylinder(handle-Vector((0,0,.13)),v,.018,.012,'BareSteel',sides=24)
collider((.29,-.01,1.05),(.58,.10,1.83))
export_mesh('SM_Staff_SearchLockerDoor_V1',merge_groups(),kind='Body',hulls=HULLS)
records[-1]['asset']=BASE+'/Meshes/'+records[-1]['name']
door=bpy.data.objects[records[-1]['name']];door.location=(0,-36,0)

# Carry the complete V4 room source; replace only locker catalogue/instances.
with bpy.data.libraries.load(str(ROOT/'IntactTilesV4/Authored/StaffLivingTheme_IntactTilesV4.blend'),link=False) as (src,dst):
    dst.objects=[n for n in src.objects if not any(s in n for s in ('Locker','ChangingLocker'))]
for obj in dst.objects:
    if obj:bpy.context.scene.collection.objects.link(obj)
placements=[]
for room,offset in zip(CFG['rooms'],CFG['preview_placements_m']):
    for part in room['furniture']:
        if part['prototype'] not in ('Locker','LockerOpen'):continue
        identity=room['id']+'.'+part['id']
        name=room['id']+'_'+part['id']
        b=body.copy();b.data=body.data;b.name=name+'_Body'
        bpy.context.scene.collection.objects.link(b)
        b.location=Vector(offset)+Vector(part['position'])
        b.rotation_euler.z=math.radians(part['yaw_blender_deg'])
        hinge=bpy.data.objects.new(name+'_Hinge',None);bpy.context.scene.collection.objects.link(hinge)
        hinge.location=b.location+b.rotation_euler.to_matrix()@Vector((-.29,-.284,0))
        hinge.rotation_euler=b.rotation_euler.copy()
        d=door.copy();d.data=door.data;d.name=name+'_Door';bpy.context.scene.collection.objects.link(d)
        d.parent=hinge;d.location=(0,0,0);d.rotation_euler=(0,0,0)
        placements.append(dict(room_id=room['id'],part_id=part['id'],container_id=identity,
            position=part['position'],yaw_blender_deg=part['yaw_blender_deg'],body=records[0]['asset'],
            door=records[1]['asset'],hinge_cm=[-29,28.4,0],opened_yaw_ue=100))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'StaffLivingTheme_SearchContainersV1.blend'))
(OUT/'manifest.json').write_text(json.dumps(dict(objects=records,containers=placements,
    actor_class='/Script/FPSGAME.ColdSteelSceneContainer',rewards_deferred=True,tests_run=False,
    rendered=False,source_units='metres; UE centimetres'),ensure_ascii=False,indent=2),encoding='utf8')
print('STAFF_SEARCH_CONTAINERS_AUTHORED',len(placements),flush=True)
