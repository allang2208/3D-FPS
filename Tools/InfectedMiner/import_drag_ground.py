"""Import the enlarged pickaxe and drag/ground-slam clips into the current miner."""
import unreal,json
from pathlib import Path
ROOT=Path(unreal.Paths.project_dir())/'SourceAssets/InfectedMiner20260913/DragGround/Delivery'
DEST='/Game/Monsters/InfectedMiner/DragGround20260913'
lib=unreal.EditorAssetLibrary
accepted=unreal.load_asset('/Game/Monsters/InfectedMiner/PickaxeSingleHand20260913/SK_InfectedMiner_Pickaxe')
report=json.loads((ROOT/'rebuild.json').read_text())
def import_asset(file,name,options):
    task=unreal.AssetImportTask();task.filename=str(ROOT/file)
    task.destination_path=DEST;task.destination_name=name;task.options=options
    task.automated=True;task.replace_existing=True;task.save=True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    asset=unreal.load_asset(DEST+'/'+name)
    if not asset:raise RuntimeError('Import failed: '+name)
    return asset
options=unreal.FbxImportUI();options.automated_import_should_detect_type=False
options.mesh_type_to_import=unreal.FBXImportType.FBXIT_SKELETAL_MESH
options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False
options.import_materials=False;options.import_textures=False;options.create_physics_asset=False
options.skeleton=accepted.skeleton
options.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False)
options.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose',False)
options.skeletal_mesh_import_data.set_editor_property('vertex_color_import_option',unreal.VertexColorImportOption.REPLACE)
mesh=import_asset('SK_InfectedMiner_DragGround.fbx','SK_InfectedMiner_DragGround',options)
materials={str(slot.material_slot_name):slot.material_interface for slot in accepted.materials}
slots=list(mesh.materials)
for i,slot in enumerate(slots):slot.material_interface=materials[str(slot.material_slot_name)];slots[i]=slot
mesh.set_editor_property('materials',slots)
mesh.set_editor_property('physics_asset',accepted.get_editor_property('physics_asset'))
lib.save_loaded_asset(mesh,False)
clips={}
for state in ['Idle','Walk','Attack']:
    options=unreal.FbxImportUI();options.automated_import_should_detect_type=False
    options.mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION
    options.skeleton=accepted.skeleton;options.import_mesh=False;options.import_animations=True
    options.import_materials=False;options.import_textures=False
    options.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    options.anim_sequence_import_data.set_editor_property('custom_sample_rate',30)
    asset=import_asset(f'A_Miner_{state}.fbx',f'A_Miner_DragGround_{state}',options)
    unreal.AnimationLibrary.remove_all_animation_notify_tracks(asset)
    asset.set_preview_skeletal_mesh(mesh);lib.save_loaded_asset(asset,False)
    clips[state]=asset;report['clips'][state]['path']=asset.get_path_name()
bp=unreal.load_asset('/Game/Monsters/InfectedMiner/BP_InfectedMiner')
cdo=unreal.get_default_object(bp.generated_class())
cdo.set_editor_property('visual_mesh',mesh);cdo.mesh.set_skeletal_mesh_asset(mesh)
for state,clip in clips.items():cdo.set_editor_property(state.lower()+'_clip',clip)
cdo.set_editor_property('contact_time',report['contact_time']);cdo.set_editor_property('contact_end',report['contact_end'])
lib.save_loaded_asset(bp,False)
report['delivery_mesh']=mesh.get_path_name();report['blueprint']=bp.get_path_name()
(ROOT/'rebuild.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('MINER_DRAG_GROUND_IMPORTED '+json.dumps(report))
