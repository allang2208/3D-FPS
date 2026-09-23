"""Save only the five runtime PKM buttstock clips via background commandlet."""
import hashlib, json, shutil
from pathlib import Path
import unreal as u
O=Path(__file__).parent
PROJECT=O.parents[2]
P='/Game/Weapons/PKMLowpoly20260922'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
source=json.loads((O/'animations.json').read_text())
skeleton=u.load_asset(P+'/SK_PKM_Manny_Skeleton')
compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
if not skeleton or not compression:raise RuntimeError('PKM skeleton or viewmodel compression missing')
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
report={}
try:
    for family,info in source.items():
        folder=P+'/Animations' if family=='base' else P+'/Accessories14/Animations/'+family
        path=folder+'/'+info['name']
        disk=PROJECT/'Content'/Path(path.removeprefix('/Game/')+'.uasset')
        backup=O/'BeforeImport'/family/disk.name
        backup.parent.mkdir(parents=True,exist_ok=True)
        if disk.exists() and not backup.exists():shutil.copy2(disk,backup)
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
        opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.skeleton=skeleton
        d=opt.anim_sequence_import_data
        d.set_editor_property('use_default_sample_rate',False)
        d.set_editor_property('custom_sample_rate',info['fps'])
        d.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        task=u.AssetImportTask();task.filename=str(O/'Animations'/family/(info['name']+'.fbx'))
        task.destination_path=folder;task.destination_name=info['name'];task.options=opt;task.factory=u.FbxFactory()
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
        A.import_asset_tasks([task]);anim=u.load_asset(path)
        if not task.imported_object_paths or not anim:raise RuntimeError('Animation import failed: '+family)
        anim.set_editor_property('bone_compression_settings',compression)
        E.set_metadata_tag(anim,'PKMCombatRevision','Melee24; own stock arc, fixed grips and complete arm support')
        if not E.save_asset(path,False):raise RuntimeError('Animation save failed: '+family)
        report[family]={'asset':anim.get_path_name(),'saved':True,'duration':anim.get_play_length(),
            'fps':info['fps'],'previous_backup':str(backup),'sha256':hashlib.sha256(disk.read_bytes()).hexdigest()}
        (O/'import_receipt.json').write_text(json.dumps(report,indent=2))
        print('PKM24_ANIMATION_SAVED',family,flush=True)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
print('PKM24_ALL_ANIMATIONS_SAVED',flush=True)
