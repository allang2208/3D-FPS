"""Import the corrected rigid head on the existing skeleton and materials."""
import unreal,json
from pathlib import Path
ROOT=Path(unreal.Paths.project_dir())/'SourceAssets/InfectedMiner20260913/PickaxeSingleHand/Delivery'
DEST='/Game/Monsters/InfectedMiner/PickaxeSingleHand20260913'
lib=unreal.EditorAssetLibrary
accepted=unreal.load_asset('/Game/Monsters/InfectedMiner/AuthoredChopFinal/SK_InfectedMiner')
options=unreal.FbxImportUI()
options.automated_import_should_detect_type=False
options.mesh_type_to_import=unreal.FBXImportType.FBXIT_SKELETAL_MESH
options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False
options.import_materials=False;options.import_textures=False;options.create_physics_asset=False
options.skeleton=accepted.skeleton
options.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False)
options.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose',False)
options.skeletal_mesh_import_data.set_editor_property('vertex_color_import_option',unreal.VertexColorImportOption.REPLACE)
task=unreal.AssetImportTask();task.filename=str(ROOT/'SK_InfectedMiner_Pickaxe.fbx')
task.destination_path=DEST;task.destination_name='SK_InfectedMiner_Pickaxe'
task.options=options;task.automated=True;task.replace_existing=True;task.save=True
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
mesh=unreal.load_asset(DEST+'/SK_InfectedMiner_Pickaxe')
if not mesh:raise RuntimeError('Pickaxe mesh import failed')
materials={str(slot.material_slot_name):slot.material_interface for slot in accepted.materials}
slots=list(mesh.materials)
for i,slot in enumerate(slots):
    slot.material_interface=materials[str(slot.material_slot_name)];slots[i]=slot
mesh.set_editor_property('materials',slots)
mesh.set_editor_property('physics_asset',accepted.get_editor_property('physics_asset'))
lib.save_loaded_asset(mesh,False)
report=json.loads((ROOT/'rebuild.json').read_text())
for clip in report['clips'].values():
    asset=unreal.load_asset(clip['path']);asset.set_preview_skeletal_mesh(mesh);lib.save_loaded_asset(asset,False)
bp=unreal.load_asset('/Game/Monsters/InfectedMiner/BP_InfectedMiner')
cdo=unreal.get_default_object(bp.generated_class())
cdo.set_editor_property('visual_mesh',mesh);cdo.mesh.set_skeletal_mesh_asset(mesh)
lib.save_loaded_asset(bp,False)
report['delivery_mesh']=mesh.get_path_name()
(ROOT/'rebuild.json').write_text(json.dumps(report,indent=2))
unreal.log('MINER_PICK_HEAD_IMPORTED '+mesh.get_path_name())
