"""Replace the rejected spliced grips in place. Keep current M249 surface materials."""
import hashlib
import json
from pathlib import Path
import zipfile

import unreal as ue


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
MESHES = '/Game/Weapons/M249/CommonParts20261108/Meshes'
PLACEMENTS = json.loads((HERE/'placement.json').read_text())
OLD = json.loads((HERE.parent/'GripMount40/saved.json').read_text())
OLD.update({p:r['sha256'] for p,r in json.loads((HERE.parent/'RearGrip43/saved.json').read_text()).items()})
RECEIPT = HERE/'saved.json'


def file_for(path):
    return PROJECT/'Content'/(path.removeprefix('/Game/')+'.uasset')


def digest(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def replace(path, key, fbx):
    mesh = ue.load_asset(path)
    body_slot = 'M24913_'+key+'_1'
    slot, = [s for s in mesh.static_materials if body_slot in
             (str(s.material_slot_name),str(s.get_editor_property('imported_material_slot_name')))]
    material = slot.material_interface
    if not material:
        raise RuntimeError('Missing current grip surface '+path)
    options = ue.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = ue.FBXImportType.FBXIT_STATIC_MESH
    options.import_mesh = True
    options.import_as_skeletal = options.import_textures = options.import_materials = False
    data = options.static_mesh_import_data
    data.combine_meshes = True
    data.generate_lightmap_u_vs = data.auto_generate_collision = False
    data.vertex_color_import_option = ue.VertexColorImportOption.REPLACE
    data.normal_import_method = ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task = ue.AssetImportTask()
    task.filename = str(fbx)
    task.destination_path, task.destination_name = path.rsplit('/',1)
    task.automated = task.replace_existing = task.replace_existing_settings = True
    task.save = False
    task.options = options
    ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if list(task.imported_object_paths) != [path+'.'+task.destination_name]:
        raise RuntimeError('Could not import the original grip at '+path)
    mesh = ue.load_asset(path)
    if mesh.get_num_sections(0) != 1:
        raise RuntimeError('Unexpected extra mesh section after removing the connector '+path)
    editor = ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem) or ue.new_object(ue.StaticMeshEditorSubsystem)
    index = editor.get_lod_material_slot(mesh,0,0)
    if not 0 <= index < len(mesh.static_materials):
        raise RuntimeError('Unmapped material on the original grip '+path)
    if mesh.get_material(index) != material:
        mesh.set_material(index,material)
    ue.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh)
    if not ue.EditorAssetLibrary.save_loaded_asset(mesh,False):
        raise RuntimeError('Save failed '+path)
    return dict(sha256=digest(file_for(path)),fbx=digest(fbx),surface=material.get_path_name(),
                sections=1,source_triangles=mesh.get_num_triangles(0))


def publish():
    if '-run=' not in ue.SystemLibrary.get_command_line().lower() and ue.get_editor_subsystem(ue.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('M249_ORIGINAL_GRIP_WAIT_FOR_PIE')
    saved = json.loads(RECEIPT.read_text()) if RECEIPT.exists() else {}
    paths = {k:MESHES+'/SM_M249_'+k for k in PLACEMENTS}
    dirty = {p.get_path_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    for path in paths.values():
        if path in dirty or digest(file_for(path)) != saved.get(path,{}).get('sha256',OLD[path]):
            raise RuntimeError('Production grip changed '+path)
    backup = PROJECT/'trash/M249RearGrip44/before.zip'
    backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():
        with zipfile.ZipFile(backup,'x',zipfile.ZIP_DEFLATED) as archive:
            for path in paths.values():
                file = file_for(path)
                archive.write(file,file.relative_to(PROJECT))
    flag = 'Interchange.FeatureFlags.Import.FBX'
    previous = ue.SystemLibrary.get_console_variable_int_value(flag)
    ue.SystemLibrary.execute_console_command(None,flag+' 0')
    try:
        for key, path in paths.items():
            fbx = HERE/'Exports'/('SM_M249_'+key+'.fbx')
            if saved.get(path,{}).get('fbx') != digest(fbx):
                saved[path] = replace(path,key,fbx)
                RECEIPT.write_text(json.dumps(saved,indent=2))
                ue.log('M249_ORIGINAL_GRIP_SAVED '+path)
    finally:
        ue.SystemLibrary.execute_console_command(None,flag+' '+str(previous))


publish()
