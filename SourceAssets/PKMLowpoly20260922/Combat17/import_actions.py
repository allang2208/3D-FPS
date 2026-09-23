"""Install PKM combat clips at existing runtime paths; no PIE/test launch."""
import json
import unreal as u
from pathlib import Path
O=Path(__file__).parent
P='/Game/Weapons/PKMLowpoly20260922'
E=u.EditorAssetLibrary
A=u.AssetToolsHelpers.get_asset_tools()
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('End PIE before PKM combat animation import')
source=json.loads((O/'animations.json').read_text())
report=json.loads((O/'imported.json').read_text()) if (O/'imported.json').exists() else {}
skeleton=u.load_asset(P+'/SK_PKM_Manny_Skeleton')
compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
flag='Interchange.FeatureFlags.Import.FBX'
prior=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for key,info in source.items():
        family,clip=key.split('/')
        if family!=FAMILY or key in report:continue
        target=P+'/Animations' if family=='base' else P+'/Accessories14/Animations/'+family
        opt=u.FbxImportUI()
        opt.automated_import_should_detect_type=False
        opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        opt.import_mesh=False;opt.import_animations=True
        opt.import_materials=False;opt.import_textures=False;opt.skeleton=skeleton
        d=opt.anim_sequence_import_data
        d.set_editor_property('use_default_sample_rate',False)
        d.set_editor_property('custom_sample_rate',info['fps'])
        d.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        task=u.AssetImportTask()
        task.filename=str(O/'Animations'/family/(info['name']+'.fbx'))
        task.destination_path=target;task.destination_name=info['name']
        task.options=opt;task.factory=u.FbxFactory();task.automated=True
        task.replace_existing=True;task.replace_existing_settings=True;task.save=False
        A.import_asset_tasks([task])
        anim=u.load_asset(target+'/'+info['name'])
        if not task.imported_object_paths or not anim:raise RuntimeError('Import failed '+key)
        anim.set_editor_property('bone_compression_settings',compression)
        E.set_metadata_tag(anim,'PKMCombatRevision','Combat17; tactical sprint / fitted stock melee')
        if not E.save_loaded_asset(anim,False):raise RuntimeError('Save failed '+key)
        report[key]={'asset':anim.get_path_name(),'seconds':anim.get_play_length(),'saved':True}
        (O/'imported.json').write_text(json.dumps(report,indent=2))
finally:
    u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
print('PKM17_COMBAT_FAMILY_SAVED',FAMILY)
