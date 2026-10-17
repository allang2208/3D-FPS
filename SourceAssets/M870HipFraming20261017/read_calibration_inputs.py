"""Sample saved idle poses for the SUPER90-relative M870 placement calculation."""
import json
from pathlib import Path
import unreal as u

output = Path(__file__).parent
clips = {
    'm4': '/Game/Weapons/M4ContactImpactFinal/A_AKM_idle',
    'super90': '/Game/Weapons/Super90/Cransh20261006/Animations/A_Super90_idle',
    'm870': '/Game/Weapons/M870/Tactical20261015/Animations/A_M870_idle',
}
result = {'purpose': 'production calibration inputs, no gameplay test', 'seconds': 0.0, 'clips': {}}
for name, path in clips.items():
    clip = u.load_asset(path)
    if not clip:
        raise RuntimeError('Missing idle: ' + path)
    options = u.AnimPoseEvaluationOptions()
    options.evaluation_type = u.AnimDataEvalType.COMPRESSED
    pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, 0.0, options)
    bones = {}
    for bone in ('hand_r', 'WPN_root', 'WPN_RearSight', 'WPN_FrontSight'):
        t = u.AnimPoseExtensions.get_bone_pose(pose, bone, u.AnimPoseSpaces.WORLD)
        p, q = t.translation, t.rotation
        bones[bone] = {'p': [p.x, p.y, p.z], 'q_xyzw': [q.x, q.y, q.z, q.w]}
    result['clips'][name] = {'path': clip.get_path_name(), 'bones': bones}
(output / 'calibration_inputs.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('M870_HIP_CALIBRATION_INPUTS_SAVED')
