"""Save R8 reloads, fitted receiver guide, loader props and grip deltas.

The main weapon, shared skeleton, materials and non-loader clips retain
their current authoring. No gameplay, renderer or validation test is run here.
"""
import json, shutil, hashlib
from pathlib import Path
import unreal as u

if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Exit PIE before replacing Super90 reload animations; no assets changed.')

O=Path(__file__).parent; P=O.parents[1]
SOURCE=O.parent/'Super90Speedloader20261007'
D='/Game/Weapons/Super90/Speedloader20261007/Animations'
E=u.EditorAssetLibrary; A=u.AssetToolsHelpers.get_asset_tools()
manifest=json.loads((SOURCE/'authoring.json').read_text(encoding='utf-8'))
if manifest['revision']!='ContactR8-20261008':
    raise RuntimeError('Export the R8 contact flow before this import.')
receipt={'completed':False,'revision':manifest['revision'],'saved':[],'profiles':{},'runtime_tested':False}

def record():
    (O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')

def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing '+path)
    return obj

def backup(path):
    relative=path.split('.')[0].removeprefix('/Game/')+'.uasset'
    src=P/'Content'/relative; dst=O/'Before'/'Content'/relative
    if src.exists() and not dst.exists():
        dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)

def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+obj.get_path_name())
    receipt['saved'].append(obj.get_path_name());record()

families=('vertical','canted','prism','angled')
profile_paths={f:'/Game/Weapons/Super90/Foregrips20261007/Profiles/DA_Super90_'+f for f in families}
for clip in manifest['clips']:backup(D+'/'+clip['name'])
for path in profile_paths.values():backup(path)
props_path=D.rsplit('/',1)[0]+'/SK_Super90_LoaderProps'
backup(props_path)
guide_path=D.rsplit('/',1)[0]+'/SM_Super90_LoaderGuide'
backup(guide_path)
guide_materials={str(slot.get_editor_property('material_slot_name')):
    slot.get_editor_property('material_interface').get_path_name()
    for slot in load(guide_path).get_editor_property('static_materials')}

def material_paths(mesh):
    # Keep plain paths, never references into an array that reimport replaces.
    return {str(slot.get_editor_property('material_slot_name')):
            slot.get_editor_property('material_interface').get_path_name()
            for slot in mesh.get_editor_property('materials')}

saved_materials=material_paths(load(props_path))

skeleton=load('/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7').skeleton
compression=load('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
flag='Interchange.FeatureFlags.Import.FBX'
previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for clip in manifest['clips']:
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
        opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        opt.import_mesh=False;opt.import_as_skeletal=False;opt.import_animations=True
        opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
        opt.skeleton=skeleton
        opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
        opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
        task=u.AssetImportTask();task.filename=clip['file'];task.destination_name=clip['name'];task.destination_path=D
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
        task.factory=u.FbxFactory();task.options=opt;A.import_asset_tasks([task])
        if not task.imported_object_paths:raise RuntimeError('FBX import failed '+clip['name'])
        obj=load(D+'/'+clip['name']);obj.set_editor_property('bone_compression_settings',compression)
        E.set_metadata_tag(obj,'Super90SpeedloaderSource',manifest['revision']+'; continuous elbow transport, fitted support palm and outside thumb-release approach; original ammo/cue clock')
        E.set_metadata_tag(obj,'Super90SourceSHA256',hashlib.sha256(Path(clip['file']).read_bytes()).hexdigest())
        save(obj)
finally:
    u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))

def snapshot_other_clips(asset,family):
    # Function scope drops all reflected struct views before array replacement.
    payload={'family':family,'clips':[]}; retained={}
    for clip in asset.get_editor_property('clips'):
        base=clip.get_editor_property('base').get_path_name()
        if base.startswith(D+'/'):continue
        payload['clips'].append({'base':base,'duration':float(clip.get_editor_property('duration')),'tracks':[
            {'bone':str(t.get_editor_property('bone')),'times':list(t.get_editor_property('times')),'values':list(t.get_editor_property('values'))}
            for t in clip.get_editor_property('tracks')]})
        original=clip.get_editor_property('retained')
        if original:retained[base]=original.get_path_name()
    return payload,retained

for family,path in profile_paths.items():
    asset=load(path);combined,retained=snapshot_other_clips(asset,family)
    combined['clips'].extend(json.loads((SOURCE/(family+'_profiles.json')).read_text(encoding='utf-8'))['clips'])
    if not asset.set_shared_clips_from_json(json.dumps(combined)):raise RuntimeError('Grip extension failed '+family)
    if retained:
        rows=list(asset.get_editor_property('clips'))
        for index,row in enumerate(rows):
            base=row.get_editor_property('base').get_path_name()
            if base in retained:row.set_editor_property('retained',load(retained[base]));rows[index]=row
        asset.set_editor_property('clips',rows)
    E.set_metadata_tag(asset,'Super90SpeedloaderGrip',manifest['revision']+'; sprint and original clips retained')
    save(asset);receipt['profiles'][family]={'path':path,'clip_count':len(combined['clips'])};record()
receipt['completed']=True;record()
print('SUPER90_CONTACT_FLOW_R8_SAVED',len(receipt['saved']),flush=True)
