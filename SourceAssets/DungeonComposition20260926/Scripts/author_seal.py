"""Author a reusable doorway closure with the approved corridor surface library."""
import os,json,random,copy
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1]
for folder in ('Config','Authored','Receipts','Sources'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
LIB=ROOT.parent/'DungeonRoomShells20260922/Scripts/author_rooms.py'
config=json.loads((LIB.parents[1]/'Config/rooms.json').read_text(encoding='utf-8'))
(ROOT/'Config/rooms.json').write_text(json.dumps(dict(seed=92626,style=config['style'],rooms=[]),indent=2))
os.environ['DUNGEON_AUTHOR_ROOT']=str(ROOT)
scope={'__file__':str(LIB),'__name__':'door_seal_author'}
exec(compile(LIB.read_text(encoding='utf-8').split("for index,room in enumerate(CFG['rooms']):",1)[0],str(LIB),'exec'),scope)
room=copy.deepcopy(config['rooms'][0]);room.update(id='DoorSeal',origin_m=[0,0,0],height_m=2.87)
scope.update(ROOM=room,GROUPS={},R=random.Random(92626))
# 6 cm of concealed overlap behind the existing jambs and 7 cm behind the lintel.
scope['wall']((-1.56,0),(1.56,0),2.87)
scope['export']()
# Fracture edge faces can inherit a collapsed atlas UV from the surface library.
# Give only those triangles their own planar UVs before producing the final FBX.
repaired=0
for record in scope['RECORDS']:
    if record['kind']!='Tiles':continue
    obj=bpy.data.objects[record['name']];mesh=obj.data;uv=mesh.uv_layers.active.data
    for face in mesh.polygons:
        loops=list(face.loop_indices)
        if len(loops)!=3:continue
        a,b,c=[uv[i].uv.copy() for i in loops]
        if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))>1.e-10:continue
        axis=max(range(3),key=lambda i:abs(face.normal[i]));dims=[i for i in range(3) if i!=axis]
        for li in loops:
            co=mesh.vertices[mesh.loops[li].vertex_index].co
            uv[li].uv=(co[dims[0]]/2,co[dims[1]]/2)
        repaired+=1
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=record['fbx'],use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/DungeonDoorSeal.blend'))
(ROOT/'Authored/manifest.json').write_text(json.dumps(dict(objects=scope['RECORDS']),indent=2))
print('DUNGEON_DOOR_SEAL_AUTHORED',len(scope['RECORDS']),flush=True)
print('DOOR_SEAL_PLANAR_EDGE_UVS',repaired,flush=True)
