"""Import the ten authored reloads at their existing paths and save packages.

Native compressed samples are retained for the user's requested sleeve/arm
diagnosis. No world, PIE, game, screenshot or unrelated validation is started.
"""
import json, hashlib, shutil, sys
from pathlib import Path
import unreal as u

O=Path(__file__).parent
P=O.parents[1]
BASE=json.loads((P/'SourceAssets/ChainmailCameraClearance20260929/SVD/poses.json').read_text())
receipt_path=O/'import_receipt.json'
receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def disk(path):return P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def pack(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return dict(p=[p.x,p.y,p.z],q=[q.x,q.y,q.z,q.w],s=[s.x,s.y,s.z])

jobs=[]
for family in ('base','angled','canted','prism','vertical'):
    for clip in ('reload','reload_empty'):
        report=json.loads((O/f'authoring_{family}_{clip}.json').read_text())
        folder='Complete20260923' if family=='base' else 'Accessories20260923'
        path='/Game/Weapons/SVDDragunov20260922/'+folder+'/Animations/'+report['action']
        jobs.append((family+'/'+clip,path,report))
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Active play session; no animation overwrite')
for key,path,report in jobs:
    if key in receipt:continue
    if path in dirty:raise RuntimeError('Unsaved target animation: '+path)
    if sha(disk(path))!=BASE['clips'][path]:raise RuntimeError('Target changed since source diagnosis: '+path)
    if not Path(report['fbx']).is_file():raise RuntimeError('Missing exported animation: '+key)

flag='Interchange.FeatureFlags.Import.FBX'
prior=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for key,path,report in jobs:
        if key in receipt:continue
        old=u.load_asset(path)
        if not old:raise RuntimeError('Missing animation '+path)
        backup=O/'Before'/Path(path.removeprefix('/Game/')+'.uasset')
        backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():shutil.copy2(disk(path),backup)
        preserved={n:old.get_editor_property(n) for n in ('bone_compression_settings','curve_compression_settings','enable_root_motion','force_root_lock','root_motion_root_lock','use_normalized_root_motion_scale')}
        opts=u.FbxImportUI()
        opts.automated_import_should_detect_type=False
        opts.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        opts.import_mesh=False;opts.import_animations=True
        opts.import_materials=False;opts.import_textures=False
        opts.skeleton=old.get_editor_property('skeleton')
        data=opts.anim_sequence_import_data
        data.set_editor_property('use_default_sample_rate',False)
        data.set_editor_property('custom_sample_rate',120)
        data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        task=u.AssetImportTask()
        task.filename=report['fbx'];task.destination_path=path.rsplit('/',1)[0]
        task.destination_name=report['action'];task.options=opts;task.factory=u.FbxFactory()
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        if not task.imported_object_paths:raise RuntimeError('Import failed '+path)
        anim=u.load_asset(path)
        for name,value in preserved.items():anim.set_editor_property(name,value)
        u.EditorAssetLibrary.set_metadata_tag(anim,'SVDArmPlaneAuthoring','20260930: anatomical upper hinge, palm-guided forearm, matched segment helpers; immutable wrist/fingers/weapon; runtime visual pending')
        if not u.EditorAssetLibrary.save_loaded_asset(anim,False):raise RuntimeError('Save failed '+path)
        receipt[key]=dict(asset=anim.get_path_name(),saved=True,source=report['fbx'],source_sha256=sha(report['fbx']),before=str(backup),before_sha256=sha(backup),saved_sha256=sha(disk(path)),duration=anim.get_play_length(),skeleton=opts.skeleton.get_path_name(),game_tested=False)
        receipt_path.write_text(json.dumps(receipt,indent=2))
        print('SVD_ARM_PLANE_SAVED',key,flush=True)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))

native=u.load_asset(BASE['native'])
options=u.AnimPoseEvaluationOptions(optional_skeletal_mesh=native,evaluation_type=u.AnimDataEvalType.COMPRESSED)
samples=[];clips={}
for key,path,report in jobs:
    anim=u.load_asset(path)
    for old in (p for p in BASE['poses'] if p['clip']==path):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(anim,old['time'],options)
        samples.append(dict(clip=path,time=old['time'],bones={n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in old['bones']}))
    clips[path]=sha(disk(path))
(O/'compressed-poses.json').write_text(json.dumps(dict(native=BASE['native'],native_sha256=sha(disk(BASE['native'])),clips=clips,poses=samples)))
sys.path.insert(0,str(P/'Tools/ModularOutfit'))
import garment_ue
bare_path=json.loads((P/'SourceAssets/ChainmailCameraClearance20260929/SVD/bare.json').read_text())['source']
_,bare=garment_ue.source_snapshot(u.load_asset(bare_path))
bare['asset_sha256']=sha(disk(bare_path))
(O/'bare-current.json').write_text(json.dumps(bare))
print('SVD_ARM_PLANE_IMPORT_COMPLETE',len(receipt),'compressed_samples',len(samples),flush=True)
