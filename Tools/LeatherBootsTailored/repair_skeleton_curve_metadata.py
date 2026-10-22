"""Persist legacy curve metadata migration before uncooked -game loads native animations."""
import hashlib,json,shutil,sys
from pathlib import Path
import unreal as u
sys.path.insert(0,str(Path(__file__).parent));from boot_paths import *
A=R/'Audit/StartupRepair';A.mkdir(parents=True,exist_ok=True)
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    ed=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if ed and ed.is_in_play_in_editor():raise RuntimeError('End PIE before native skeleton metadata repair')
path='/Game/AsianMale_Jason/Mesh/Body/SKM_Jason_body_Skeleton';disk=P/'Content'/(path[6:]+'.uasset');raw=disk.read_bytes();backup=A/'BeforeCurveMetadata'/disk.relative_to(P)
if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(disk,backup)
skeleton=u.load_asset(path);assert skeleton
def rest():
    pose=skeleton.get_reference_pose();rows=[]
    for bone in u.AnimPoseExtensions.get_bone_names(pose):
        t=u.AnimPoseExtensions.get_bone_pose(pose,bone,u.AnimPoseSpaces.LOCAL);p,q,s=t.translation,t.rotation,t.scale3d
        rows.append([str(bone),p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z])
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest(),len(rows)
before_rest,count=rest();before=sorted(str(n) for n in u.AnimationLibrary.get_curve_meta_data_names(skeleton));loaded=[]
for clip_path in dict.fromkeys(read(P/'Content/ColdSteelData/player_body.json')['clips'].values()):
    clip=u.load_asset(clip_path);assert clip
    if clip.get_editor_property('skeleton')==skeleton:loaded.append(clip_path)
# Restore the diagnostic-only reference change; it did not explain the crash.
trial=A/'retarget_reference_repair.json'
if trial.exists():
    trials=read(trial)
    for clip_path,row in trials['assets'].items():
        clip=u.load_asset(clip_path)
        if clip.get_editor_property('retarget_source_asset') is None:
            clip.set_editor_property('retarget_source_asset',u.load_asset(row['old_reference']));u.AKMAnimationAuditLibrary.finish_animation_compression(clip)
            assert u.EditorAssetLibrary.save_loaded_asset(clip,False)
        row['diagnostic_change_restored']=True
    write(trial,trials)
after=sorted(str(n) for n in u.AnimationLibrary.get_curve_meta_data_names(skeleton));assert rest()==(before_rest,count)
assert set(before).issubset(after) and disk.read_bytes()==raw
assert u.EditorAssetLibrary.save_loaded_asset(skeleton,False)
write(A/'skeleton_curve_metadata.json',dict(completed=True,asset=skeleton.get_path_name(),before=before,after=after,added=sorted(set(after)-set(before)),loaded_native_clips=len(loaded),bone_count=count,rest_pose_sha256=before_rest,bones_and_reference_pose_unchanged=True,backup=str(backup),before_sha256=hashlib.sha256(raw).hexdigest(),after_sha256=hashlib.sha256(disk.read_bytes()).hexdigest(),runtime_retest_pending=True,root_cause='UAnimSequenceBase::PostLoad legacy curve migration invokes USkeleton::AccumulateCurveMetaData -> UEditorEngine::BeginTransaction in an uncooked -game host without GEditor. Persist native skeleton curve metadata in the editor authoring environment.'))
print('NATIVE_SKELETON_CURVE_METADATA_SAVED',len(before),len(after),sorted(set(after)-set(before)),flush=True)
