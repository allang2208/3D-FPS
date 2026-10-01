"""Import only HK416 inspect sequences and refresh the matching grip layers."""
import importlib.util
import json
import shutil
from pathlib import Path
import unreal as u

O=Path(__file__).parent
P=O.parents[1]
C=O.parent/'HK416CommonAttachments20260930'
H='/Game/Weapons/HK416/Reworked20260930'
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir())).resolve()!=(P/'Content').resolve():
    raise RuntimeError('Wrong project content')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():
    raise RuntimeError('PIE is active; preserve the running session')
source=json.loads((O/'inspect_animations.json').read_text(encoding='utf-8'))
clips=source['clips']
families=('base','vertical','canted','prism','angled','drum')
if set(clips)!={f+'/inspect' for f in families}:
    raise RuntimeError('Unexpected inspect import scope')
targets={H+'/Animations/'+c['family']+'/'+c['name'] for c in clips.values()}
profiles={'/Game/Weapons/AnimationProfiles20261001/ue_hk416/DA_'+f for f in families if f!='base'}
mesh=u.load_asset(H+'/SK_HK416_Manny')
skeleton=mesh.get_editor_property('skeleton')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty & (targets|profiles|{skeleton.get_outermost().get_name()}):
    raise RuntimeError('Preserve unsaved HK416 animation/profile edits')
for path in targets|profiles:
    file=P/'Content'/(path.removeprefix('/Game/')+'.uasset')
    backup=O/'Before'/file.relative_to(P/'Content')
    if file.exists() and not backup.exists():
        backup.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(file,backup)
receipt={'animations':{},'runtime_profiles':{},'runtime_tested':False,'duration':source['duration']}
def record():
    (O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
tools=u.AssetToolsHelpers.get_asset_tools()
flag='Interchange.FeatureFlags.Import.FBX'
previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for key,clip in clips.items():
        path=H+'/Animations/'+clip['family']+'/'+clip['name']
        old=u.load_asset(path)
        if not old:
            raise RuntimeError('Missing active HK416 inspect clip '+path)
        compression=old.get_editor_property('bone_compression_settings')
        opt=u.FbxImportUI()
        opt.automated_import_should_detect_type=False
        opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        opt.import_mesh=False
        opt.import_animations=True
        opt.import_materials=False
        opt.import_textures=False
        opt.skeleton=skeleton
        opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
        opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
        task=u.AssetImportTask()
        task.filename=clip['file']
        task.destination_path=H+'/Animations/'+clip['family']
        task.destination_name=clip['name']
        task.automated=True
        task.replace_existing=True
        task.save=False
        task.options=opt
        tools.import_asset_tasks([task])
        anim=u.load_asset(path)
        anim.set_editor_property('bone_compression_settings',compression)
        u.EditorAssetLibrary.set_metadata_tag(anim,'HK416InspectSource',
            '20261001 AKM/SVD shared rifle trajectory; native grip; 4.2 s; 120 Hz; whole arms')
        if not u.EditorLoadingAndSavingUtils.save_packages([anim.get_outermost()],False):
            raise RuntimeError('Save failed '+path)
        receipt['animations'][key]={'asset':anim.get_path_name(),'source':clip['file'],
            'saved':True,'duration':anim.get_play_length()}
        record()
finally:
    u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
spec=importlib.util.spec_from_file_location('hk416_inspect_profiles',C/'import_grip_profiles.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
receipt['runtime_profiles']=module.refresh_inspect_profiles(O)
receipt['status']='six inspect animations and five runtime grip profiles saved'
record()
print('HK416_INSPECT_SAVED',len(receipt['animations']),len(receipt['runtime_profiles']),flush=True)
