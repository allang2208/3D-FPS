"""Publish the pin partition to the native rig, the movable mount and the assembly table."""
from pathlib import Path
import hashlib
import json
import zipfile
import unreal as ue

project = Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir()))
here = project/'SourceAssets/M249Orpind20261107/BipodPin41'
expected = json.loads((here/'inputs.json').read_text())
receipt = here/'saved.json'
saved = json.loads(receipt.read_text()) if receipt.exists() else {}
rig_path = '/Game/Weapons/M249/SK_M249_V7'

def file(path):
    return project/'Content'/(path[6:]+'.uasset')

def digest(path):
    return hashlib.sha256(file(path).read_bytes()).hexdigest()

def save(path, mesh):
    if not ue.EditorAssetLibrary.save_loaded_asset(mesh, False):
        raise RuntimeError('Cannot save '+path)
    saved[path] = digest(path)
    receipt.write_text(json.dumps(saved, indent=2))
    print('M249_BIPOD_PIN_SAVED', path, flush=True)

def import_part(path):
    old = ue.load_asset(path)
    materials = {str(slot.get_editor_property('imported_material_slot_name')): slot.material_interface
                 for slot in old.static_materials}
    folder, name = path.rsplit('/', 1)
    task = ue.AssetImportTask()
    task.filename = str(here/'Exports'/(name+'.fbx'))
    task.destination_name = name
    task.destination_path = folder
    task.automated = True
    task.replace_existing = True
    opt = ue.FbxImportUI()
    opt.automated_import_should_detect_type = False
    opt.mesh_type_to_import = ue.FBXImportType.FBXIT_STATIC_MESH
    opt.import_mesh = True
    opt.import_materials = False
    opt.import_textures = False
    opt.static_mesh_import_data.combine_meshes = True
    opt.static_mesh_import_data.auto_generate_collision = False
    opt.static_mesh_import_data.generate_lightmap_u_vs = False
    opt.static_mesh_import_data.normal_import_method = ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task.options = opt
    ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not task.imported_object_paths: raise RuntimeError('Cannot import '+name)
    mesh = ue.load_asset(path)
    for i, slot in enumerate(mesh.static_materials):
        material = materials.get(str(slot.get_editor_property('imported_material_slot_name')))
        if not material and len(set(materials.values())) == 1: material = next(iter(materials.values()))
        if not material: raise RuntimeError('Missing original surface on '+name)
        mesh.set_material(i,material)
    ue.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh)
    save(path,mesh)

if '-run=' not in ue.SystemLibrary.get_command_line().lower():
    if ue.get_editor_subsystem(ue.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('M249_BIPOD_PIN_WAIT_FOR_PIE')
dirty = {p.get_path_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for path, original in expected.items():
    if path in dirty or digest(path) != saved.get(path,original):
        raise RuntimeError('Production asset changed: '+path)
if not (here/'before.zip').exists():
    with zipfile.ZipFile(here/'before.zip','x',zipfile.ZIP_DEFLATED) as backup:
        for path in expected: backup.write(file(path),file(path).relative_to(project))
if rig_path not in saved:
    mesh = ue.load_asset(rig_path)
    centers = [ue.Vector(*p) for p in json.loads((here/'pin.json').read_text())['centers']]
    if not ue.M24ChassisAssetTools.move_factory_faces(mesh,'M249_Factory_Receiver','M249_Bipod',centers):
        raise RuntimeError('Native pin repartition failed')
    save(rig_path,mesh)
flag = 'Interchange.FeatureFlags.Import.FBX'
previous = ue.SystemLibrary.get_console_variable_int_value(flag)
ue.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for path in expected:
        if path not in saved: import_part(path)
finally:
    ue.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
print('M249_BIPOD_PIN_PUBLISHED',len(saved),flush=True)
