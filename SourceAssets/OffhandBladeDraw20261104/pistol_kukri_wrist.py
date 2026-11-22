"""Export the left wrist's authored rotation relative to its settled pistol carry."""
from pathlib import Path
import math
import unreal as u


def export(output):
    mesh = u.load_asset('/Game/Weapons/FrostCrystalSword20260915/Modules20260915/SK_FrostSword_Arms')
    clip = u.load_asset('/Game/Weapons/TacticalHatchet20261101/OffhandDraw/Arms/A_OffhandKukriEquip')
    if not mesh or not clip:
        raise RuntimeError('Missing kukri draw or native arms')
    cfg = u.AnimPoseEvaluationOptions()
    cfg.optional_skeletal_mesh = mesh
    cfg.evaluation_type = u.AnimDataEvalType.SOURCE
    count = round(clip.get_play_length() * 60)
    rotations = []
    for i in range(count + 1):
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, min(i / 60, clip.get_play_length()), cfg)
        hand = u.AnimPoseExtensions.get_bone_pose(pose, 'hand_l', u.AnimPoseSpaces.WORLD)
        q = hand.rotation
        # The native mesh faces camera +X after its 90-degree yaw.
        rotations.append(u.Quat(-q.y, q.x, q.z, q.w))
    q = rotations[-1]
    inverse_end = u.Quat(-q.x, -q.y, -q.z, q.w)
    lines = ['#pragma once', '// Generated from the left wrist of A_OffhandKukriEquip at 60 Hz.',
             'namespace PistolKukriDraw', '{', '    inline constexpr float WristRotation[][4]={']
    peak = 0
    for rotation in rotations:
        relative = rotation * inverse_end
        peak = max(peak, math.degrees(2 * math.acos(min(1.,abs(relative.w)))))
        lines.append('        {' + ','.join(f'{v:.7f}f' for v in (relative.x, relative.y, relative.z, relative.w)) + '},')
    lines.extend(['    };','}'])
    Path(output).write_text('\n'.join(lines)+'\n',encoding='utf8')
    return {'samples':count+1,'peak_degrees_from_carry':peak,'seconds':clip.get_play_length()}
