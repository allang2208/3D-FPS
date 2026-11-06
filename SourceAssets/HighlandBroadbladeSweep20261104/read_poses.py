"""Capture installed grip-specific idle and the braked pose of the heavy stroke."""
from pathlib import Path
import json
import unreal as u

out = {}
for grip, folder in [('Standard', '/Game/Weapons/AzureRunesword20260913'),
                     ('LongGrip', '/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations')]:
    poses = {}
    for key, role, time in [('idle', 'Idle', 0.), ('land', 'HeavyRelease', .2375)]:
        clip = u.load_asset(folder + '/A_RuneSword_' + role)
        options = u.AnimPoseEvaluationOptions()
        options.evaluation_type = u.AnimDataEvalType.SOURCE
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, time, options)
        bones = {}
        for name in u.AnimPoseExtensions.get_bone_names(pose):
            tf = u.AnimPoseExtensions.get_bone_pose(pose, name, u.AnimPoseSpaces.LOCAL)
            p, q, s = tf.translation, tf.rotation, tf.scale3d
            bones[str(name)] = dict(p=[p.x,p.y,p.z], q=[q.w,q.x,q.y,q.z], s=[s.x,s.y,s.z])
        poses[key] = bones
        poses['skeleton'] = clip.get_editor_property('skeleton').get_path_name()
    out[grip] = poses
Path(__file__).with_name('grip_poses.json').write_text(json.dumps(out))
