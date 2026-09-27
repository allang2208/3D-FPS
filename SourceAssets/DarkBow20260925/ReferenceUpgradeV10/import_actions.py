"""Background import/save of V10 animations on the existing bow skeleton."""
import json
from pathlib import Path
import unreal as u

P=Path(__file__).parent
DEST='/Game/Weapons/DarkBow20260925/ReferenceUpgradeV10'
INFO=json.loads((P/'authoring.json').read_text())
E=u.EditorAssetLibrary
A=u.AssetToolsHelpers.get_asset_tools()
receipt_path=P/'import-receipt.json'
receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else {'saved':{},'runtime_tested':False}
mesh=u.load_asset('/Game/Weapons/DarkBow20260925/ContactV9/SK_Bow_BareArmsV7')
if not mesh:raise RuntimeError('ContactV9 bow arms are required')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
for role in INFO['durations']:
    name='A_Bow_'+role
    if name in receipt['saved']:continue
    if E.does_asset_exist(DEST+'/'+name):
        raise RuntimeError('Preserve pre-existing unowned asset '+name)
    opt=u.FbxImportUI()
    opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    opt.import_mesh=False;opt.import_animations=True
    opt.import_materials=False;opt.import_textures=False
    opt.skeleton=mesh.skeleton
    opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',INFO['fps'])
    opt.anim_sequence_import_data.set_editor_property('remove_redundant_keys',False)
    task=u.AssetImportTask()
    task.filename=str(P/'Export'/(name+'.fbx'))
    task.destination_path=DEST;task.destination_name=name
    task.automated=True;task.replace_existing=False;task.save=False;task.options=opt
    A.import_asset_tasks([task])
    asset=u.load_asset(DEST+'/'+name)
    if not asset:raise RuntimeError('Import did not produce '+name)
    if compression:asset.set_editor_property('bone_compression_settings',compression)
    asset.set_preview_skeletal_mesh(mesh)
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+name)
    receipt['saved'][name]=asset.get_path_name()
    receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print('DARKBOW_V10_SAVED',asset.get_path_name())
print('DARKBOW_V10_IMPORT_COMPLETE',len(receipt['saved']))
