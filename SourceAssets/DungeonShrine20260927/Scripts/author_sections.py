"""Split shrine fracture faces into their own material slot; preserve authored geometry."""
import json
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Authored';OUT.mkdir(parents=True,exist_ok=True)
ASSETS=ROOT.parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC'
bpy.context.scene.unit_settings.scale_length=1
sources=[
    ('DungeonAtmosphereV2_20260921','DungeonAtmosphereV2_Structure.blend','SM_V2_Breach_Structural','Breach',
     'DGN_A_AV2_Breach_Structural','/Game/Dungeons/AtmosphereV2/Structure/SM_V2_Breach_Structural'),
    ('DungeonRoomInteriors20260921','DungeonRooms_Authored.blend','SM_Room_RU_Threshold','Threshold',
     'DGN_A_Room_RU_Threshold','/Game/Dungeons/AtmosphereV2/RoomInteriors/Authored/SM_Room_RU_Threshold'),
    ('DungeonRoomInteriors20260921','DungeonRooms_Authored.blend','SM_Room_RU_Overhang','Overhang',
     'DGN_A_Room_RU_Overhang','/Game/Dungeons/AtmosphereV2/RoomInteriors/Authored/SM_Room_RU_Overhang'),
    ('DungeonRoomInteriors20260921','DungeonRooms_Authored.blend','SM_Room_RU_OldFlagstones','Flagstones',
     'DGN_A_Room_RU_OldFlagstones','/Game/Dungeons/AtmosphereV2/RoomInteriors/Authored/SM_Room_RU_OldFlagstones')]
records=[]
for folder,blend,name,kind,label,source_mesh in sources:
    with bpy.data.libraries.load(str(ASSETS/folder/'Authored'/blend),link=False) as (src,dst):
        dst.objects=[name]
    obj=dst.objects[0]
    if obj is None:raise RuntimeError('Missing authored mesh '+name)
    bpy.context.scene.collection.objects.link(obj)
    obj.name='SM_Shrine_'+kind
    obj.data.materials.clear()
    for slot in ('ShrineStoneSurface','ShrineStoneCut') if kind=='Flagstones' else ('ShrineConcrete','ShrineConcreteCut'):
        obj.data.materials.append(bpy.data.materials.get(slot) or bpy.data.materials.new(slot))
    cut_count=0
    for face in obj.data.polygons:
        n=face.normal
        cut=abs(n.y)<.65 if kind=='Breach' else abs(n.z)<.7
        face.material_index=1 if cut else 0
        cut_count+=int(cut)
    if not cut_count:raise RuntimeError('No section faces in '+name)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    path=OUT/(obj.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
    records.append(dict(name=obj.name,fbx=str(path),actor=label,source_mesh=source_mesh,cut_faces=cut_count,
        material_slots=[m.name for m in obj.data.materials]))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ShrineSections_Editable.blend'))
(OUT/'sections.json').write_text(json.dumps(dict(objects=records,tests_run=False),indent=2),encoding='utf-8')
print('SHRINE_SECTION_ASSETS_AUTHORED',len(records))
