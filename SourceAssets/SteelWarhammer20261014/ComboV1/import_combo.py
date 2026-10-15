"""Import and save the four new combo clips without modifying shared packages."""
import unreal as u, json
from pathlib import Path
P=Path(__file__).resolve().parent
R=P.parents[2]
D='/Game/Weapons/SteelWarhammer20261014/ComboV1'
if Path(u.Paths.project_dir()).resolve()!=R:raise RuntimeError('Wrong project')
commandlet='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if not commandlet and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Stop PIE before importing')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
skeleton=u.load_asset('/Game/Items/ProductionTools/RusticPickaxe20260919/SK_RusticPickaxe').skeleton
compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
receipt={'saved':[],'complete':False,'runtime_tested':False}
for suffix in ('Slash1','Slash2','Slash1Recover','Slash2Recover'):
    name='A_Warhammer_'+suffix
    anim=u.load_asset(D+'/'+name)
    if not anim:
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.skeleton=skeleton
        opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
        opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',150)
        task=u.AssetImportTask();task.filename=str(P/'Export'/(name+'.fbx'));task.destination_path=D;task.destination_name=name
        task.automated=True;task.save=False;task.replace_existing=False;task.options=opt
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        anim=u.load_asset(D+'/'+name)
    if not anim:raise RuntimeError('Import failed: '+name)
    if compression:anim.set_editor_property('bone_compression_settings',compression)
    if not u.EditorLoadingAndSavingUtils.save_packages([anim.get_outermost()],False):raise RuntimeError('Save failed: '+name)
    receipt['saved'].append(anim.get_path_name())
    (P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
receipt['complete']=True
(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(receipt))
