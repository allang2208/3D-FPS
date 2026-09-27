"""Import and save the authored bow action on its existing native skeleton."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).parent
DEST='/Game/Weapons/DarkBow20260925/QuickCombat20260926'
NAME='A_Bow_QuickCombat'
E=u.EditorAssetLibrary
receipt=P/'import-receipt.json'
if E.does_asset_exist(DEST+'/'+NAME) and not receipt.exists():
    raise RuntimeError('Unowned existing bow action; preserve it.')
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name()==DEST+'/'+NAME]
if dirty:raise RuntimeError('Preserve unsaved bow action '+str(dirty))
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
mesh=u.load_asset('/Game/Weapons/DarkBow20260925/ContactV9/SK_Bow_BareArmsV7')
info=json.loads((P/'authoring.json').read_text())
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.skeleton=mesh.skeleton
opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',info['fps'])
opt.anim_sequence_import_data.set_editor_property('remove_redundant_keys',False)
task=u.AssetImportTask();task.filename=str(P/'Export'/(NAME+'.fbx'))
task.destination_path=DEST;task.destination_name=NAME
task.automated=True;task.replace_existing=receipt.exists();task.save=False;task.options=opt
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
asset=u.load_asset(DEST+'/'+NAME)
if not asset:raise RuntimeError('Bow action import failed')
compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
if compression:asset.set_editor_property('bone_compression_settings',compression)
asset.set_preview_skeletal_mesh(mesh)
if not E.save_loaded_asset(asset,False):raise RuntimeError('Bow action save failed')
receipt.write_text(json.dumps({'saved':asset.get_path_name(),'runtime_tested':False},indent=2),encoding='utf-8')
print('BOW_QUICK_COMBAT_SAVED',asset.get_path_name())
