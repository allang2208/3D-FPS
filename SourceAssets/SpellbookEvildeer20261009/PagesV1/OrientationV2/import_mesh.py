"""Reimport only the UV-corrected book mesh, preserving skeleton and materials."""
from pathlib import Path
import json
import unreal as u

HERE = Path('D:/FPS3D/FPSGAME/SourceAssets/SpellbookEvildeer20261009/PagesV1/OrientationV2')
DEST = '/Game/Weapons/SpellbookEvildeer20261009/PagesV1/Meshes'
NAME = 'SK_Spellbook_Alchemy_16Pages'
mesh = u.load_asset(DEST+'/'+NAME)
original_materials = {str(s.material_slot_name): s.material_interface for s in mesh.get_editor_property('materials')}
skeleton = mesh.get_editor_property('skeleton')
options = u.FbxImportUI()
options.automated_import_should_detect_type = False
options.import_mesh = True
options.import_as_skeletal = True
options.import_animations = False
options.import_materials = False
options.import_textures = False
options.create_physics_asset = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_SKELETAL_MESH
options.skeleton = skeleton
data = options.skeletal_mesh_import_data
data.convert_scene = True
data.convert_scene_unit = False
data.import_uniform_scale = 1.
data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
data.set_editor_property('bUpdateSkeletonReferencePose', False)
data.set_editor_property('bUseT0AsRefPose', False)
task = u.AssetImportTask()
task.filename = str(HERE.parent/'Export'/(NAME+'.fbx'))
task.destination_path = DEST
task.destination_name = NAME
task.automated = True
task.replace_existing = True
task.save = False
task.options = options
flag = 'Interchange.FeatureFlags.Import.FBX'
previous = u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError('Book mesh import produced no asset')
    mesh = u.load_asset(DEST+'/'+NAME)
    slots = list(mesh.get_editor_property('materials'))
    for slot in slots:
        slot.set_editor_property('material_interface', original_materials[str(slot.material_slot_name)])
    mesh.set_editor_property('materials', slots)
    if not u.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False):
        raise RuntimeError('Unable to save the UV-corrected book mesh')
    receipt = dict(saved=True, mesh=mesh.get_path_name(), rotated_degrees=180,
        skeleton=skeleton.get_path_name(), material_assets_modified=False,
        texture_assets_modified=False, animation_assets_modified=False, runtime_tested=False)
    (HERE/'import-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('SPELLBOOK_PAGE_ORIENTATION_SAVED '+json.dumps(receipt))
finally:
    u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
