"""Import/save only the four new modular static meshes; reuse the current steel/wood material."""
import json
from pathlib import Path
import unreal as u

P = Path(globals().get('__file__') or r'D:\FPS3D\FPSGAME\SourceAssets\KukriModules20261026\import_modules.py').resolve().parent
source = json.loads((P / 'modules.json').read_text(encoding='utf-8'))
tools = u.AssetToolsHelpers.get_asset_tools()
editor = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
material = u.load_asset('/Game/Weapons/Kukri20261020/Materials/M_Kukri')
if not material:
    raise RuntimeError('Original M_Kukri material unavailable')
receipt = {'complete': False, 'saved_assets': [], 'runtime_tested': False}
for slot, part in source['parts'].items():
    package = part['mesh'].split('.')[0]
    task = u.AssetImportTask()
    task.filename = part['fbx']
    task.destination_path, task.destination_name = package.rsplit('/', 1)
    task.automated = True
    task.replace_existing = True
    task.save = False
    options = u.FbxImportUI()
    options.import_mesh = True
    options.import_as_skeletal = False
    options.import_materials = False
    options.import_textures = False
    options.import_animations = False
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    data = options.static_mesh_import_data
    data.combine_meshes = True
    data.auto_generate_collision = False
    data.generate_lightmap_u_vs = True
    data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task.options = options
    tools.import_asset_tasks([task])
    mesh = u.load_asset(package)
    if not mesh:
        raise RuntimeError('Import failed: ' + package)
    mesh.set_material(0, material)
    settings = editor.get_lod_build_settings(mesh, 0)
    settings.recompute_normals = False
    settings.recompute_tangents = True
    settings.use_mikk_t_space = True
    settings.use_high_precision_tangent_basis = True
    settings.use_full_precision_u_vs = True
    editor.set_lod_build_settings(mesh, 0, settings)
    # Preserve the accepted 3.4k-triangle source's non-Nanite shading route.
    nanite = mesh.get_editor_property('nanite_settings')
    nanite.enabled = False
    mesh.set_editor_property('nanite_settings', nanite)
    u.EditorAssetLibrary.set_metadata_tag(mesh, 'Kukri.Module', slot)
    u.EditorAssetLibrary.set_metadata_tag(mesh, 'Kukri.ModuleSource', str(P / 'Kukri_Modules_Editable.blend'))
    if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()], False):
        raise RuntimeError('Save failed: ' + package)
    receipt['saved_assets'].append(mesh.get_path_name())
    (P / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
receipt['complete'] = True
(P / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
u.log('KUKRI_MODULES_SAVED ' + json.dumps(receipt))
