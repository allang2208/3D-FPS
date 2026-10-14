"""Export persisted body donors and the equipment grip for offline authoring.

Reads source assets only. Does not sample a live pawn, open a level or run PIE.
"""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT/'SourceAssets/ThirdPersonSwordActions20261006'
OUT.mkdir(parents=True, exist_ok=True)
cfg = json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
mesh = u.load_asset(cfg['body_mesh'])
component = u.new_object(u.SkeletalMeshComponent)
component.set_skeletal_mesh_asset(mesh)
ref = mesh.skeleton.get_reference_pose()
names = [str(n) for n in u.AnimPoseExtensions.get_bone_names(ref)]
parents = [names.index(str(component.get_parent_bone(n))) if str(component.get_parent_bone(n)) in names else -1 for n in names]

def pack(t):
    return [t.translation.x, t.translation.y, t.translation.z,
            t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w,
            t.scale3d.x, t.scale3d.y, t.scale3d.z]

options = u.AnimPoseEvaluationOptions()
options.optional_skeletal_mesh = mesh
options.evaluation_type = u.AnimDataEvalType.SOURCE
clips = {}
for label, role in [('idle', 'Melee.FullBody.Idle'), ('chop', 'Melee.FullBody.Overhead'), ('grip', 'Melee.Grip')]:
    clip = u.load_asset(cfg['clips'][role])
    duration = clip.get_play_length()
    count = max(2, round(duration*60)+1)
    frames = []
    for i in range(count):
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, duration*i/(count-1), options)
        frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose, n, u.AnimPoseSpaces.LOCAL)) for n in names])
    clips[label] = dict(asset=clip.get_path_name(), duration=duration, frames=frames)

# Bind/idle hand anatomy is equipment calibration, not FPS attack animation.
native = u.load_asset('/Game/Weapons/AzureRunesword20260913/Modules20260919/SK_RuneSword_Arms')
native_ref = native.skeleton.get_reference_pose()
native_options = u.AnimPoseEvaluationOptions()
native_options.optional_skeletal_mesh = native
native_options.evaluation_type = u.AnimDataEvalType.SOURCE
native_idle = u.load_asset('/Game/Weapons/AzureRunesword20260913/A_RuneSword_Idle')
native_pose = u.AnimPoseExtensions.get_anim_pose_at_time(native_idle, 0., native_options)
native_names = [str(n) for n in u.AnimPoseExtensions.get_bone_names(native_ref)]
equipment = dict(mesh=native.get_path_name(), idle=native_idle.get_path_name(),
    reference={n: pack(u.AnimPoseExtensions.get_bone_pose(native_ref, n, u.AnimPoseSpaces.WORLD)) for n in native_names},
    pose={n: pack(u.AnimPoseExtensions.get_bone_pose(native_pose, n, u.AnimPoseSpaces.WORLD)) for n in native_names})
data = dict(mesh=mesh.get_path_name(), skeleton=mesh.skeleton.get_path_name(), names=names, parents=parents,
    reference=[pack(u.AnimPoseExtensions.get_bone_pose(ref, n, u.AnimPoseSpaces.LOCAL)) for n in names],
    clips=clips, equipment=equipment)
(OUT/'authoring-input.json').write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
print('SWORD_ACTIONS_PREPARED '+str(OUT/'authoring-input.json'))
