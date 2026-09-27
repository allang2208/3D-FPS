"""Save V23 locomotion clips on the existing V7 arms skeleton; no gameplay launch."""
import json,hashlib
from pathlib import Path
import unreal as u
P=Path(__file__).parent; DEST='/Game/Weapons/DarkBow20260925/LocomotionV23'
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Stop Play before saving bow locomotion assets')
E=u.EditorAssetLibrary; A=u.AssetToolsHelpers.get_asset_tools()
receipt=P/'import-receipt.json'
r=json.loads(receipt.read_text()) if receipt.exists() else {'saved':{},'hashes':{},'gameplay_tested':False}
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name().startswith(DEST+'/')]
if dirty:raise RuntimeError('Preserving unsaved packages '+str(dirty))
mesh=u.load_asset('/Game/Weapons/DarkBow20260925/ContactV9/SK_Bow_BareArmsV7')
compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
info=json.loads((P/'authoring.json').read_text(encoding='utf8'))
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
for role in info['durations']:
    name='A_Bow_'+role; source=P/'Export'/(name+'.fbx'); digest=hashlib.sha256(source.read_bytes()).hexdigest()
    if name in r['saved'] and r['hashes'].get(name)==digest:continue
    if name not in r['saved'] and E.does_asset_exist(DEST+'/'+name):raise RuntimeError('Unowned existing asset '+name)
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opt.import_mesh=False;opt.import_animations=True
    opt.import_materials=False;opt.import_textures=False;opt.skeleton=mesh.skeleton
    opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',info['fps'])
    opt.anim_sequence_import_data.set_editor_property('remove_redundant_keys',False)
    task=u.AssetImportTask();task.filename=str(source);task.destination_path=DEST;task.destination_name=name
    task.automated=True;task.replace_existing=name in r['saved'];task.save=False;task.options=opt
    A.import_asset_tasks([task]);asset=u.load_asset(DEST+'/'+name)
    if not asset:raise RuntimeError('Import failed '+name)
    if compression:asset.set_editor_property('bone_compression_settings',compression)
    asset.set_preview_skeletal_mesh(mesh)
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+name)
    r['saved'][name]=asset.get_path_name();r['hashes'][name]=digest
    receipt.write_text(json.dumps(r,indent=2),encoding='utf8')
print('BOW_LOCOMOTION_V23_SAVED '+json.dumps(r))
