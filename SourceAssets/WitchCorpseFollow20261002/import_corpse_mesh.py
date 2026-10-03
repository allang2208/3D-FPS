"""Import/save the new corpse mesh and its dedicated connected-body Physics Asset."""
import json
from pathlib import Path
import unreal as u

root = Path('D:/FPS3D/FPSGAME/SourceAssets/WitchCorpseFollow20261002')
dest = '/Game/Monsters/WitchRebuilt/CorpseFollow'
lib = u.EditorAssetLibrary
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Stop PIE before importing the corpse assets')
live = u.load_asset('/Game/Monsters/WitchRebuilt/SK_WitchRebuilt')
physics_path = dest+'/PA_WitchRebuilt_CorpseFollow'
physics = (u.load_asset(physics_path) if lib.does_asset_exist(physics_path)
           else lib.duplicate_asset(live.physics_asset.get_path_name(), physics_path))
if not physics:
    raise RuntimeError('Corpse Physics Asset creation failed')
u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')
options = u.FbxImportUI()
options.automated_import_should_detect_type = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_SKELETAL_MESH
options.import_as_skeletal = True
options.import_mesh = True
options.import_animations = False
options.import_materials = False
options.import_textures = False
options.skeleton = live.skeleton
options.create_physics_asset = False
options.physics_asset = physics
data = options.skeletal_mesh_import_data
data.convert_scene = True
data.convert_scene_unit = True
data.force_front_x_axis = False
data.import_uniform_scale = 1.
data.set_editor_property('update_skeleton_reference_pose', False)
data.vertex_color_import_option = u.VertexColorImportOption.REPLACE
data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_COMPUTE_NORMALS
task = u.AssetImportTask()
task.filename = str(root/'SK_WitchRebuilt_CorpseFollow.fbx')
task.destination_path = dest
task.destination_name = 'SK_WitchRebuilt_CorpseFollow'
task.factory = u.FbxFactory()
task.options = options
task.automated = True
task.save = False
task.replace_existing = True
task.replace_existing_settings = True
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
mesh = u.load_asset(dest+'/'+task.destination_name)
if not mesh:
    raise RuntimeError('Corpse skeletal mesh import failed')
slots = list(mesh.materials)
original_slots = list(live.materials)
for slot in slots:
    name = str(slot.get_editor_property('imported_material_slot_name'))
    candidates = [s for s in original_slots if str(s.get_editor_property('imported_material_slot_name')) == name]
    if not candidates:
        category = next((c for c in ('AnatomicalSkin', 'Lining', 'UpperRobe', 'Robe', 'Head', 'Hat') if c in name), None)
        candidates = [s for s in original_slots if category and category in str(s.get_editor_property('imported_material_slot_name'))]
    if not candidates:
        raise RuntimeError('No accepted live material for corpse slot '+name)
    slot.set_editor_property('material_interface', candidates[0].get_editor_property('material_interface'))
mesh.set_editor_property('materials', slots)
mesh.set_editor_property('physics_asset', physics)
# Final corpse grounding samples the visible skinned surface once at LOD0.
u.SkeletalMeshEditorSubsystem.set_allow_cpu_access(mesh, True)
if not u.WitchRebuiltMonster.prepare_rebuilt_physics(mesh, True):
    raise RuntimeError('Connected corpse body/hinge authoring failed')
lib.set_metadata_tag(mesh, 'CorpsePresentation',
    'Single skeleton: live geometry/materials, connected death garment and retained leg skin; no cloth simulation')
lib.set_metadata_tag(mesh, 'Source', str(root/'WitchRebuilt_CorpseFollow.blend'))
for asset in (physics, mesh):
    if not lib.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed: '+asset.get_path_name())
result = dict(mesh=mesh.get_path_name(), physics=physics.get_path_name(),
              skeleton=mesh.skeleton.get_path_name(), assets_saved=True,
              live_mesh_preserved=True, materials=[s.get_editor_property('material_interface').get_path_name() for s in slots],
              runtime_tested=False)
(root/'assets.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))
