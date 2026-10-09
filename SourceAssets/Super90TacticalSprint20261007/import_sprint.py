"""Import native sprint and merge its three entries into current grip profiles."""
import unreal as u
import json, shutil
from pathlib import Path
O=Path(__file__).parent; P=O.parents[1]
D='/Game/Weapons/Super90/TacticalSprint20261007/Animations'
E=u.EditorAssetLibrary; A=u.AssetToolsHelpers.get_asset_tools()
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Exit PIE before saving Super90 sprint animations. No assets modified.')
M=json.loads((O/'authoring.json').read_text(encoding='utf-8'))
repair=O.parent/'Super90SprintArmR3_20261007'
receipt={'completed':False,'revision':M.get('revision','initial'),'saved':[],'profiles':{},'runtime_tested':False}
def record():
    payload=json.dumps(receipt,indent=2)
    (O/'import_receipt.json').write_text(payload,encoding='utf-8')
    (repair/'import_receipt.json').write_text(payload,encoding='utf-8')
def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing '+path)
    return obj
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+obj.get_path_name())
    receipt['saved'].append(obj.get_path_name());record()
def backup(obj):
    rel=obj.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset'
    src=P/'Content'/rel; dst=repair/'Before/Content'/rel
    if src.exists() and not dst.exists():
        dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
mesh=load('/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7')
compression=load('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
flag='Interchange.FeatureFlags.Import.FBX'
previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for clip in M['clips']:
        if E.does_asset_exist(clip['asset']):backup(load(clip['asset']))
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
        opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False
        opt.skeleton=mesh.skeleton
        opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
        opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
        task=u.AssetImportTask();task.filename=clip['file'];task.destination_path=D;task.destination_name=clip['name']
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
        task.factory=u.FbxFactory();task.options=opt;A.import_asset_tasks([task])
        if not task.imported_object_paths:raise RuntimeError('Sprint import failed '+clip['name'])
        asset=load(clip['asset']);asset.set_editor_property('bone_compression_settings',compression)
        E.set_metadata_tag(asset,'Super90SprintSource',M.get('revision','initial')+'; complete left shoulder/clavicle return; native hinge release; 120 Hz; unchanged geometry/skeleton')
        save(asset)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
def snapshot_other_clips(asset,family):
    # Release reflected array views at function exit before replacing Clips.
    combined={'family':family,'clips':[]}; retained={}
    for clip in asset.get_editor_property('clips'):
        base=clip.get_editor_property('base').get_path_name()
        if base.startswith(D+'/'):continue
        combined['clips'].append({'base':base,'duration':float(clip.get_editor_property('duration')),
            'tracks':[{'bone':str(t.get_editor_property('bone')),'times':list(t.get_editor_property('times')),'values':list(t.get_editor_property('values'))} for t in clip.get_editor_property('tracks')]})
        authored=clip.get_editor_property('retained')
        if authored:retained[base]=authored.get_path_name()
    return combined,retained

for family in M['families']:
    asset=load('/Game/Weapons/Super90/Foregrips20261007/Profiles/DA_Super90_'+family);backup(asset)
    combined,retained=snapshot_other_clips(asset,family)
    combined['clips'].extend(json.loads((O/(family+'_profiles.json')).read_text(encoding='utf-8'))['clips'])
    if not asset.set_shared_clips_from_json(json.dumps(combined)):raise RuntimeError('Sprint profile import failed '+family)
    if retained:
        rows=list(asset.get_editor_property('clips'))
        for index,clip in enumerate(rows):
            base=clip.get_editor_property('base').get_path_name()
            if base in retained:clip.set_editor_property('retained',load(retained[base]));rows[index]=clip
        asset.set_editor_property('clips',rows)
    E.set_metadata_tag(asset,'Super90TacticalSprint',M.get('revision','initial')+'; whole left shoulder return and native hinge release; existing reload and loader actions retained')
    save(asset);receipt['profiles'][family]={'path':asset.get_path_name(),'clips':len(combined['clips'])};record()
receipt['completed']=True;record();print('SUPER90_TACTICAL_SPRINT_SAVED',len(receipt['saved']),flush=True)
