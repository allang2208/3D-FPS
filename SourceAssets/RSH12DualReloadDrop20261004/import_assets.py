"""Save only the two dual reload profiles and detached cartridge meshes."""
import unreal as u, json, shutil
from pathlib import Path

O = Path(__file__).resolve().parent
P = O.parents[1]
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
root = '/Game/Weapons/RSH12/DualReloadDrop20261004'
auth = json.loads((O/'authoring.json').read_text())
profiles = {side:'/Game/Weapons/RSH12/Native71520261003/Profiles/DA_RSH12_'+side+'_base' for side in ('r', 'l')}
targets = set(profiles.values()) | {root+'/'+m['name'] for m in auth['meshes']}
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('PIE is active; reload assets remain on disk')
if targets & {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
    raise RuntimeError('Target reload assets have unsaved edits')
receipt = dict(complete=False, saved=[], runtime_tested=False)
def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Cannot save '+asset.get_path_name())
    receipt['saved'].append(asset.get_path_name())
    (O/'import_receipt.json').write_text(json.dumps(receipt, indent=2))
for path in targets:
    disk = P/'Content'/(path.removeprefix('/Game/')+'.uasset')
    backup = O/'BeforeAssets'/(path.removeprefix('/Game/')+'.uasset')
    if disk.exists() and not backup.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(disk, backup)
material = u.load_asset('/Game/Weapons/RSH12/Materials/MI_RSH12_SourcePBR')
if not material:
    raise RuntimeError('Missing source RSH cartridge material')
flag = 'Interchange.FeatureFlags.Import.FBX'
old = u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None, flag+' 0')
try:
    for m in auth['meshes']:
        opts = u.FbxImportUI()
        opts.automated_import_should_detect_type = False
        opts.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
        opts.import_as_skeletal = False
        opts.import_materials = False
        opts.import_textures = False
        opts.static_mesh_import_data.combine_meshes = True
        opts.static_mesh_import_data.auto_generate_collision = False
        opts.static_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        task = u.AssetImportTask()
        task.filename = m['fbx']
        task.destination_path = root
        task.destination_name = m['name']
        task.automated = True
        task.replace_existing = True
        task.replace_existing_settings = True
        task.options = opts
        task.factory = u.FbxFactory()
        A.import_asset_tasks([task])
        mesh = u.load_asset(root+'/'+m['name'])
        if not mesh:
            raise RuntimeError('Cartridge import failed '+m['name'])
        mesh.set_material(0, material)
        save(mesh)
    for side, path in profiles.items():
        profile = u.load_asset(path)
        if not profile or not profile.set_shared_clips_from_json((O/side/'profile.json').read_text()):
            raise RuntimeError('Dual profile import failed '+side)
        E.set_metadata_tag(profile, 'DualReloadDrop', 'RSH12DualReloadDrop20261004; lower during opening; donor low reload handoff')
        save(profile)
finally:
    u.SystemLibrary.execute_console_command(None, flag+' '+str(old))
receipt['complete'] = True
(O/'import_receipt.json').write_text(json.dumps(receipt, indent=2))
print('RSH12_RELOAD_DROP_SAVED', flush=True)
