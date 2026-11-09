"""Save the M249-native M24 hand action and its runtime selector in the background."""
from pathlib import Path
import unreal as u,json,gzip,hashlib
r=Path(__file__).resolve().parent;E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
dest='/Game/Weapons/M249/Bipod';clip_path=dest+'/A_M249_Bipod';profile_path=dest+'/DA_M249_Bipod'
if '-run=' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('PIE active; preserve loaded assets until play stops')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection((clip_path,profile_path)):raise RuntimeError('Unsaved bipod assets retained')
receipt_path=r/'import_receipt.json';prior=json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
for path in (clip_path,profile_path):
    if E.does_asset_exist(path) and path not in prior.get('saved_packages',[])+prior.get('created_packages',[]):raise RuntimeError('Existing unowned asset retained '+path)
prior['created_packages']=[clip_path,profile_path];receipt_path.write_text(json.dumps(prior,indent=2))
mesh=u.load_asset('/Game/Weapons/M249/SK_M249_V7')
clip=u.load_asset(clip_path) if E.does_asset_exist(clip_path) else E.duplicate_asset('/Game/Weapons/M249/Animations/A_M249_idle',clip_path)
payload=(r/'bipod.json.gz').read_bytes();data=json.loads(gzip.decompress(payload))
ctl=clip.get_editor_property('controller');ctl.open_bracket('M249 fitted M24 bipod pull and reversible return',False)
try:
    # 600 Hz is the common integral bridge from the retained 60 Hz idle to 200 Hz.
    ctl.set_frame_rate(u.FrameRate(numerator=600,denominator=1),False)
    ctl.set_number_of_frames(u.FrameNumber(value=round(data['duration']*600)),False)
    ctl.set_frame_rate(u.FrameRate(numerator=data['fps'],denominator=1),False)
    ctl.set_number_of_frames(u.FrameNumber(value=round(data['duration']*data['fps'])),False)
    for bone,rows in data['tracks'].items():
        ctl.add_bone_curve(bone,False)
        if not ctl.set_bone_track_keys(bone,[u.Vector(*v[:3]) for v in rows],[u.Quat(*v[3:7]) for v in rows],[u.Vector(*v[7:]) for v in rows],False):raise RuntimeError('Bone write '+bone)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Populate bipod action')
finally:ctl.close_bracket(False)
clip.set_preview_skeletal_mesh(mesh);clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.REF_POSE)
if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip) or not E.save_loaded_asset(clip,False):raise RuntimeError('Save bipod action')
receipt=dict(saved_packages=[clip_path],saved=[clip.get_path_name()],runtime_tested=False,complete=False,
    created_packages=[clip_path,profile_path],payload_sha256=hashlib.sha256(payload).hexdigest())
receipt_path.write_text(json.dumps(receipt,indent=2))
profile=u.load_asset(profile_path) if E.does_asset_exist(profile_path) else None
if not profile:
    factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeaponGripProfile)
    profile=AT.create_asset('DA_M249_Bipod',dest,u.WeaponGripProfile,factory)
# Different native skeleton: keep one fitted sequence. Reverse sampling supplies
# retraction; no second full clip and no M24 grip deltas on the M249 hierarchy.
if not profile.set_shared_clips_from_json(json.dumps(dict(family='bipod',clips=[dict(base=clip.get_path_name(),duration=data['duration'],tracks=[])]))):raise RuntimeError('Set native bipod profile')
if not E.save_loaded_asset(profile,False):raise RuntimeError('Save bipod profile')
receipt['saved_packages'].append(profile_path);receipt['saved'].append(profile.get_path_name());receipt['complete']=True
receipt['asset_hashes']={path:hashlib.sha256((Path(u.Paths.project_content_dir())/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest() for path in receipt['saved_packages']}
receipt_path.write_text(json.dumps(receipt,indent=2))
print('M249_BIPOD_HAND_ACTION_SAVED',len(receipt['saved']),flush=True)
