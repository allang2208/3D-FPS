"""Save only the five equip/empty-reload pairs to the existing PKM routes."""
import json, shutil
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P='/Game/Weapons/PKMLowpoly20260922'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
commandlet='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if not commandlet:
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():raise RuntimeError('PKM31: end PIE before replacing animations')
source=json.loads((O/'animations.json').read_text())
targets={}
for key,info in source.items():
    family,clip=key.split('/')
    folder=P+'/Animations' if family=='base' else P+'/Accessories14/Animations/'+family
    targets[key]=folder+'/'+info['name']
if not commandlet:
    dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    conflict=set(targets.values())&dirty
    if conflict:raise RuntimeError('PKM31 unsaved target animations: '+str(sorted(conflict)))
skeleton=u.load_asset(P+'/SK_PKM_Manny_Skeleton')
compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
if not skeleton or not compression:raise RuntimeError('Missing current PKM skeleton/compression')
project=Path(u.Paths.project_dir()).resolve()
report={};flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for key,info in source.items():
        family,clip=key.split('/');path=targets[key];folder=path.rsplit('/',1)[0]
        disk=project/'Content'/(path.removeprefix('/Game/')+'.uasset')
        backup=O/'BeforeImport'/family/disk.name
        if disk.exists() and not backup.exists():
            backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(disk,backup)
        options=u.FbxImportUI();options.automated_import_should_detect_type=False
        options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        options.import_mesh=False;options.import_animations=True
        options.import_materials=False;options.import_textures=False;options.skeleton=skeleton
        data=options.anim_sequence_import_data
        data.set_editor_property('use_default_sample_rate',False)
        data.set_editor_property('custom_sample_rate',info['fps'])
        data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        task=u.AssetImportTask();task.filename=str(O/'Animations'/family/(info['name']+'.fbx'))
        task.destination_path=folder;task.destination_name=info['name'];task.options=options
        task.factory=u.FbxFactory();task.automated=True;task.replace_existing=True
        task.replace_existing_settings=True;task.save=False
        A.import_asset_tasks([task]);anim=u.load_asset(path)
        if not task.imported_object_paths or not anim:raise RuntimeError('PKM31 animation import failed: '+key)
        anim.set_editor_property('bone_compression_settings',compression)
        E.set_metadata_tag(anim,'PKMEquipChargeRevision','EquipCharge31: video raise/catch/settle; overhand pad contact, full-segment wrist support')
        if not E.save_loaded_asset(anim,False):raise RuntimeError('PKM31 save failed: '+key)
        report[key]={'asset':anim.get_path_name(),'saved':True,'duration':anim.get_play_length(),
                     'fps':info['fps'],'game_tested':False}
        (O/'import_receipt.json').write_text(json.dumps(report,indent=2))
        print('PKM31_ANIMATION_SAVED',key,flush=True)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
print('PKM31_ALL_ANIMATIONS_SAVED',flush=True)
