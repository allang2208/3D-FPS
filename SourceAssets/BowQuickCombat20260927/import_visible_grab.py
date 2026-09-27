"""Replace only this task's bow quick-combat clip; preserve the prior binary."""
import json,shutil
from pathlib import Path
import unreal as u
P=Path(__file__).parent;ROOT=P.parents[1]
DEST='/Game/Weapons/DarkBow20260925/QuickCombat20260926';NAME='A_Bow_QuickCombat'
E=u.EditorAssetLibrary
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Finish PIE before importing/saving the bow action.')
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name()==DEST+'/'+NAME]
if dirty:raise RuntimeError('Preserve unsaved bow action '+str(dirty))
owner=json.loads((P.parent/'BowQuickCombat20260926/import-receipt.json').read_text())
if owner['saved']!=DEST+'/'+NAME+'.'+NAME:raise RuntimeError('Unexpected existing action owner')
backup=P/'Before';backup.mkdir(exist_ok=True)
binary=ROOT/'Content/Weapons/DarkBow20260925/QuickCombat20260926'/f'{NAME}.uasset'
if not (backup/binary.name).exists():shutil.copy2(binary,backup/binary.name)
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
task.automated=True;task.replace_existing=True;task.save=False;task.options=opt
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
asset=u.load_asset(DEST+'/'+NAME)
if not asset:raise RuntimeError('Bow action import failed')
compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
if compression:asset.set_editor_property('bone_compression_settings',compression)
asset.set_preview_skeletal_mesh(mesh)
u.AKMAnimationAuditLibrary.finish_animation_compression(asset)
if not E.save_loaded_asset(asset,False):raise RuntimeError('Bow action save failed')
(P/'import-receipt.json').write_text(json.dumps({'saved':asset.get_path_name(),'prior_binary':str(backup/binary.name),
    'source':'generated_action_v2.py','runtime_tested':False},indent=2),encoding='utf-8')
print('BOW_VISIBLE_GRAB_SAVED',asset.get_path_name())
source=(P/'inspect_grab.py').read_text().replace('imported-before.json','imported-after.json')
exec(compile(source,str(P/'inspect_grab.py'),'exec'),{'__file__':str(P/'inspect_grab.py')})
