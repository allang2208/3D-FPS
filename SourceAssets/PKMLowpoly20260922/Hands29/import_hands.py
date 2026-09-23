"""Import corrected primary UVs only; preserve PKM rig, sections and materials."""
import json
import shutil
import sys
from pathlib import Path
import unreal as u

O = Path(__file__).parent
R = O.parent
P = '/Game/Weapons/PKMLowpoly20260922'
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
project = Path(u.Paths.project_dir()).resolve()
commandlet = '-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if not commandlet:
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('PKM29: stop PIE before replacing the skeletal mesh')

mesh = u.load_asset(P+'/Accessories14/SK_PKM_Manny_Modular')
skeleton = mesh.skeleton
if not skeleton.get_path_name().startswith(P+'/'):
    raise RuntimeError('Expected existing PKM private skeleton')
targets = {a.get_path_name().split('.')[0] for a in (mesh, skeleton)}
if not commandlet:
    conflict = targets & {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if conflict:
        raise RuntimeError('PKM29 target has unsaved changes: '+str(sorted(conflict)))

for asset in (mesh, skeleton):
    package = asset.get_path_name().split('.')[0]
    source = project/'Content'/(package.removeprefix('/Game/')+'.uasset')
    destination = O/'BeforeImport'/source.relative_to(project/'Content')
    if source.exists() and not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

sys.path.insert(0, str(R/'Belt08'))
from material_binding import capture_bindings, bind_materials
bindings = capture_bindings(mesh)
(O/'materials_before.json').write_text(json.dumps({k:v.get_path_name() for k,v in bindings.items()}, indent=2))

options = u.FbxImportUI()
options.automated_import_should_detect_type = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_SKELETAL_MESH
options.import_as_skeletal = True
options.import_mesh = True
options.import_animations = False
options.import_materials = False
options.import_textures = False
options.create_physics_asset = False
options.skeleton = skeleton
data = options.skeletal_mesh_import_data
data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
data.set_editor_property('update_skeleton_reference_pose', False)
data.set_editor_property('use_t0_as_ref_pose', False)
data.set_editor_property('preserve_smoothing_groups', True)
task = u.AssetImportTask()
task.filename = str(O/'Exports/SK_PKM_Manny_Modular.fbx')
task.destination_path = P+'/Accessories14'
task.destination_name = 'SK_PKM_Manny_Modular'
task.options = options
task.factory = u.FbxFactory()
task.automated = True
task.replace_existing = True
task.replace_existing_settings = True
task.save = False
flag = 'Interchange.FeatureFlags.Import.FBX'
prior = u.SystemLibrary.get_console_variable_int_value(flag)
try:
    u.SystemLibrary.execute_console_command(None, flag+' 0')
    A.import_asset_tasks([task])
finally:
    u.SystemLibrary.execute_console_command(None, flag+' '+str(prior))
mesh = u.load_asset(P+'/Accessories14/SK_PKM_Manny_Modular')
if not mesh or not task.imported_object_paths:
    raise RuntimeError('PKM29 skeletal mesh import failed')
rows = bind_materials(mesh, {}, bindings)
E.set_metadata_tag(mesh, 'PKMHandUVRevision',
                   'Hands29: each source primary UV mapped to channel 0 before assembly join; shared Manny materials')
saved = []
for asset in (mesh, mesh.skeleton):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('PKM29 save failed: '+asset.get_path_name())
    saved.append(asset.get_path_name())
report = {'saved': saved, 'bindings': rows, 'animations_imported': False,
          'materials_rebuilt': False, 'game_tested': False,
          'source_blend': 'HandleFinish27/PKM_HandleFinish_Editable.blend',
          'fix': 'Export copies share primary UV0; original source meshes/rig/pose unchanged'}
(O/'import_receipt.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('PKM29_IMPORTED', json.dumps({'saved': saved, 'slots': len(rows), 'game_tested': False}), flush=True)
