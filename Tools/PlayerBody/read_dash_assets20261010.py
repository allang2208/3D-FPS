"""Read saved recovery arm chains from compressed animation data; no gameplay."""
import json
import math
from pathlib import Path
import unreal as u

root = Path('D:/FPS3D/FPSGAME')
out = root/'SourceAssets/ThirdPersonDashArm20261010'
saved = json.loads((out/'assets-saved.json').read_text())
source = json.loads((out/'candidate-actions.json').read_text())
mesh = u.load_asset(source['mesh'])
options = u.AnimPoseEvaluationOptions()
options.optional_skeletal_mesh = mesh
options.evaluation_type = u.AnimDataEvalType.COMPRESSED
bones = [n for n in source['names'] if n.startswith(('upperarm_', 'lowerarm_', 'hand_'))]
indices = {n: source['names'].index(n) for n in bones}
report = {'gameplay_test': False, 'clips': {}}
for key, path in saved['clips'].items():
    label = key.removeprefix('Melee.FullBody.')
    clip = u.load_asset(path)
    if not clip: raise RuntimeError('Cannot load saved animation '+path)
    c = source['clips'][label]
    markers = {str(m.marker_name): m.time for m in u.AnimationLibrary.get_animation_sync_markers(clip)}
    rotation_error = position_error = curve_error = 0.
    for frame in range(0,len(c['frames']),4):
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, frame/c['rate'], options)
        for curve,values in c['curves'].items():
            curve_error = max(curve_error, abs(u.AnimPoseExtensions.get_curve_weight(pose, curve)-values[frame]))
        for bone in bones:
            t = u.AnimPoseExtensions.get_bone_pose(pose, bone, u.AnimPoseSpaces.LOCAL)
            expected = c['frames'][frame][indices[bone]]
            actual_q = [t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w]
            dot = sum(a*b for a,b in zip(actual_q,expected[3:7]))
            norm = math.sqrt(sum(a*a for a in actual_q)*sum(b*b for b in expected[3:7]))
            rotation_error = max(rotation_error, math.degrees(2*math.acos(min(1.,abs(dot)/norm))))
            position_error = max(position_error, math.sqrt(sum((a-b)**2 for a,b in zip(
                [t.translation.x,t.translation.y,t.translation.z],expected[:3]))))
    row = dict(asset=path, markers=markers, duration=clip.get_play_length(),
        target_rate=str(clip.get_editor_property('platform_target_frame_rate').get_editor_property('default')),
        max_local_arm_rotation_error_degrees=rotation_error, max_local_arm_position_error_cm=position_error,
        max_curve_value_error=curve_error,
        skeleton_matches=clip.get_editor_property('skeleton')==mesh.skeleton,
        source_hash_matches=u.EditorAssetLibrary.get_metadata_tag(clip,'GripSourceHash')==saved['source_hash'])
    report['clips'][label] = row
    if not row['skeleton_matches'] or not row['source_hash_matches'] or not {'Contact','Release','NativeSwordGrip'}.issubset(markers):
        raise RuntimeError('Saved animation contract mismatch: '+label)
    if rotation_error > .2 or position_error > .02 or curve_error > .02:
        raise RuntimeError('Compressed arm pose differs from the accepted source: '+json.dumps(row))
(out/'asset-readback.json').write_text(json.dumps(report,indent=2))
print('KWANG_RECOVERY_READBACK '+json.dumps(report))
