"""Author the final reward annex, a real Boss rear aperture and the reused moving gate."""
import json
import math
import os
import sys
from pathlib import Path
import bpy
from mathutils import Matrix,Vector

ROOT=Path(__file__).resolve().parents[1];ASSETS=ROOT.parent
for folder in ('Authored','Config','Receipts','Sources'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
# Use the established footprint authoring library and approved corridor tile surfaces.
LIB=ASSETS/'DungeonRoomShells20260922/Scripts/author_rooms.py'
os.environ['DUNGEON_AUTHOR_ROOT']=str(ASSETS/'DungeonVentFreight20260922')
h={'__file__':str(LIB),'__name__':'reward_geometry_library'}
exec(compile(LIB.read_text(encoding='utf-8').split("for index,room in enumerate(CFG['rooms']):",1)[0],str(LIB),'exec'),h)
h['OUT']=ROOT/'Authored';h['RECORDS']=[];h['LIGHTS']=[];h['GROUPS']={}
room=dict(id='FinalRewardRoom',origin_m=[0,0,0],height_m=4.2,
    footprint=[[-2.3,26],[9.7,26],[9.7,36.5],[-2.3,36.5]],
    ceilings=[[-2.3,26.32,9.7,36.5,4.2]],beams=[],machines=[])
h['ROOM']=room
box,poly,tube,detail=h['box'],h['poly'],h['tube'],h['detail']
for key,path in {
    'BossFloor':'/Game/Dungeons/BossHall20260922/Materials/M_BossFloor',
    'BossStructuralSteel':'/Game/Dungeons/BossHall20260922/Materials/M_BossStructuralSteel',
    'Rubber':'/Game/Dungeons/AtmosphereV2/RoomInteriors/Materials/M_Room_Rubber',
    'YellowPaint':'/Game/Dungeons/AtmosphereV2/RoomInteriors/Materials/M_Room_YellowPaint',
}.items():
    h['MAPPING'][key]=path;h['MATS'][key]=bpy.data.materials.new('RS_'+key)

h['slab']([-2.3,26,9.7,36.5,0],'Floors',False,'BossFloor')
# Leave an enclosed shaft over the door so the raised leaf never cuts the ceiling.
for rect in ([-2.3,26,1.10,26.32,4.2],[6.30,26,9.7,26.32,4.2],[-2.3,26.32,9.7,36.5,4.2]):
    h['slab'](rect,'Ceilings',True)
for a,b in zip(room['footprint'][1:],room['footprint'][2:]+room['footprint'][:1]):
    h['wall'](a,b,4.2)
# Door reveal closes the existing Boss wall's cut edges, preserving the clear opening.
for x in (1.374,6.026):box('Frames',(x,26,1.57),(.028,.36,3.14),'BossStructuralSteel')
box('Frames',(3.7,26,3.145),(4.68,.36,.030),'BossStructuralSteel')
box('Frames',(3.7,26.29,4.21),(5.2,.12,.02),'BossStructuralSteel')
for x in (1.10,6.30):box('Frames',(x,26.16,4.21),(.08,.36,.02),'BossStructuralSteel')
for x in (-2.04,9.44):
    for y in (29.0,34.0):
        box('Frames',(x,y,2.1),(.28,.32,4.2),'Concrete')
        box('Frames',(x,y,.10),(.38,.42,.20),'BossStructuralSteel')
for y in (29,34):box('Frames',(3.7,y,4.04),(11.5,.24,.24),'BossStructuralSteel')
# A flush patterned bay marks the chest without a raised collision curb.
for x in (.65,3.95):box('Markings',(x,31.8,.002),(.035,2.6,.003),'YellowPaint')
for y in (30.5,33.1):box('Markings',(2.3,y,.002),(3.3,.035,.003),'YellowPaint')
# Small wall services keep the reward room in the same industrial family.
h['smooth_pipe']([(-1.94,26.35,3.68),(-1.94,36.16,3.68),(9.34,36.16,3.68)],.055)
for x in (-.9,.1):
    box('Equipment',(x,36.24,1.25),(.70,.26,1.10),'ServicePaint')
    box('Equipment',(x,36.095,1.25),(.62,.025,1.02),'PaintedSteel')
    for z in (.85,1.65):detail.fastener((x-.24,36.072,z),(0,-1,0),.009,kind='Equipment')
    tube('Equipment',[(x+.20,36.065,1.14),(x+.20,36.01,1.14),(x+.20,36.01,1.35),(x+.20,36.065,1.35)],.010,'BareSteel',20)
lights=[]
for x,y,warm,lumens in ((3.7,27.8,False,1200),(2.3,31.8,True,1800),(7.1,33.7,False,1250),(.2,35,True,700)):
    lamp=dict(at=[x,y,3.83],warm=warm,lumens=lumens,radius_cm=650)
    h['lamp'](lamp);lights.append(lamp)
    for dx in (-.34,.34):tube('Fixtures',[(x+dx,y,3.865),(x+dx,y,4.18)],.008,'BareSteel',12)
h['export']();records=list(h['RECORDS'])
for r in records:
    if r['kind'] in ('Fixtures','Markings'):r['collision']=False

# Load and clip only the three wall groups; accepted Boss machinery/gallery stays intact.
clip_source=ASSETS/'DungeonAuthoredExpansion20260922/Scripts/author_connections.py'
code=clip_source.read_text(encoding='utf-8')
scope={'bpy':bpy}
exec(compile(code[code.index('def cut('):code.index('\ndef export(')],str(clip_source),'exec'),scope)
boss_root=ASSETS/'DungeonBossHall20260922'
boss_manifest=json.loads((boss_root/'Authored/manifest.json').read_text(encoding='utf-8'))
boss_records={r['name']:r for r in boss_manifest['objects']}
def export_object(obj,path):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    tri=obj.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
for kind in ('Shell','Tiles','Frames'):
    old='SM_RS_BossPumpHall_'+kind
    with bpy.data.libraries.load(str(boss_root/'Authored/Dungeon_BossPumpHall.blend'),link=False) as (src,dst):dst.objects=[old]
    obj=dst.objects[0];bpy.context.scene.collection.objects.link(obj)
    obj.name='SM_RS_BossRewardAccess_'+kind
    scope['cut'](obj,(3.7,26,1.56),(4.64,1.0,3.16))
    path=ROOT/'Authored'/(obj.name+'.fbx');export_object(obj,path)
    records.append(dict(name=obj.name,kind=kind,room='BossRewardAccess',fbx=str(path),
        origin_m=[0,0,0],materials=boss_records[old]['materials'],collision=True))

# Original mechanical-door source, split only for this animated installation.
sys.path.insert(0,str(ASSETS/'DungeonFreightDoor20260923/Scripts'))
sys.path.insert(0,str(ASSETS/'DungeonRailCart20260923/Scripts'))
from door_geometry import build,export_lift
h['GROUPS']={};h['RECORDS']=[];h['ROOM']=dict(id='FinalRewardGate',origin_m=[0,0,0])
build(h,split=True)
# Hollow overhead cassette: leaf and pull-handle rise inside the manufactured enclosure.
for x in (6.43,11.57):box('DoorFrame',(x,17.62,5.43),(.035,.70,3.48),'FreightCoat')
for y in (17.282,17.957):box('DoorFrame',(9,y,5.43),(5.175,.024,3.48),'FreightCoat')
box('DoorFrame',(9,17.62,7.18),(5.175,.70,.026),'FreightCoat')
for x in (6.60,11.40):
    box('DoorFrame',(x,17.65,5.45),(.065,.045,3.47),'FreightTrack')
    for z in (4.1,5.5,6.9):detail.fastener((x,17.267,z),(0,-1,0),.012,kind='DoorFrame')
for kind in ('DoorFrame','DoorLeaf'):
    obj=export_lift(h,kind,'SM_RS_FinalRewardGate_'+kind)
    obj.data.transform(Matrix.Translation(Vector((-9,-17.8,-.6))))
    path=Path(h['RECORDS'][-1]['fbx']);export_object(obj,path)
    record=h['RECORDS'][-1];record['collision']=kind=='DoorFrame'
    records.append(record)
    # Source assembly placement only; FBX has a clean floor-level door pivot.
    obj.location=(3.7,26.10,0)

bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/Dungeon_FinalReward.blend'))
output=dict(objects=records,lights=lights,door_origin=[370,-2610,0],door_travel=[0,0,340],
    chest_position=[230,-3180,.8],portal_position=[710,-3370,0],tests_run=False,rendered=False)
(ROOT/'Authored/manifest.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
(ROOT/'Receipts/authoring.json').write_text(json.dumps(dict(stage='authored',mesh_count=len(records)),indent=2),encoding='utf-8')
print('FINAL_REWARD_ROOM_AUTHORED',len(records),'meshes',flush=True)
