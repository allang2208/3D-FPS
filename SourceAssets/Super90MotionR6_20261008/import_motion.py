"""Save R6 reloads, independent-pusher loader props and grip deltas in one background batch.

The main weapon, shared skeleton, guide, materials and non-loader clips retain
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
if manifest['revision']!='OpenPalmFlowR6-20261008':
    raise RuntimeError('Export the R6 open-palm flow before this import.')
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
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    opt.import_mesh=True;opt.import_as_skeletal=True;opt.import_animations=False
    opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
    opt.skeleton=skeleton
    opt.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False)
    opt.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task=u.AssetImportTask();task.filename=manifest['meshes']['props']
    task.destination_path=D.rsplit('/',1)[0];task.destination_name='SK_Super90_LoaderProps'
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    task.factory=u.FbxFactory();task.options=opt;A.import_asset_tasks([task])
    if not task.imported_object_paths:raise RuntimeError('Rebound loader prop FBX import failed')
    props=load(props_path)
    slots=list(props.get_editor_property('materials'))
    for index,slot in enumerate(slots):
        name=str(slot.get_editor_property('material_slot_name'))
        slot.set_editor_property('material_interface',load(saved_materials[name]));slots[index]=slot
    props.set_editor_property('materials',slots);props.set_editor_property('physics_asset',None)
    editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
    settings=editor.get_lod_build_settings(props,0)
    settings.use_full_precision_u_vs=True;settings.use_high_precision_tangent_basis=True
    settings.recompute_normals=False;settings.recompute_tangents=False
    editor.set_lod_build_settings(props,0,settings)
    E.set_metadata_tag(props,'Super90SpeedloaderSource',manifest['revision']+'; pusher uses unweighted native helper; release is independent from the hand')
    E.set_metadata_tag(props,'Super90SourceSHA256',hashlib.sha256(Path(manifest['meshes']['props']).read_bytes()).hexdigest())
    save(props)
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
        E.set_metadata_tag(obj,'Super90SpeedloaderSource',manifest['revision']+'; BV1Re411e77Q 40-52s open-palm return and prop fall; occluded/empty motion adapted')
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
print('SUPER90_OPEN_PALM_R6_SAVED',len(receipt['saved']),flush=True)
