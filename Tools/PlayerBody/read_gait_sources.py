"""Read-only source/retarget foot trajectory comparison for the reported tiptoe gait."""
import json
import math
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/ThirdPersonGait20261003'
OUT.mkdir(parents=True, exist_ok=True)
cfg = json.loads((ROOT / 'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
old = json.loads((ROOT / 'SourceAssets/JasonPlayer20261003/Before/Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
report = {}
for label, config in [('source', old), ('jason', cfg)]:
    mesh = u.load_asset(config['body_mesh'])
    options = u.AnimPoseEvaluationOptions()
    options.optional_skeletal_mesh = mesh
    ref = mesh.skeleton.get_reference_pose()
    def loc(pose, bone):
        return u.AnimPoseExtensions.get_bone_pose(pose, bone, u.AnimPoseSpaces.WORLD)
    def xyz(v):
        return [round(v.x, 4), round(v.y, 4), round(v.z, 4)]
    axes = {}
    for side in ('l', 'r'):
        foot, toe = loc(ref, 'foot_'+side), loc(ref, 'ball_'+side)
        axes[side] = foot.inverse_transform_direction(toe.translation-foot.translation)
    data = {'mesh': mesh.get_path_name(), 'reference': {bone: xyz(loc(ref, bone).translation)
             for bone in ('pelvis','foot_l','foot_r','ball_l','ball_r')}, 'clips': {}}
    for key, path in config['clips'].items():
        if not ('.Walk.' in key or '.Jog.' in key or key.endswith('.Idle')):
            continue
        clip = u.load_asset(path)
        samples = []
        for i in range(65):
            pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, clip.get_play_length()*i/64, options)
            sample = {}
            for side in ('l', 'r'):
                foot, toe = loc(pose, 'foot_'+side), loc(pose, 'ball_'+side)
                axis = foot.transform_direction(axes[side])
                ref_axis = loc(ref, 'ball_'+side).translation-loc(ref, 'foot_'+side).translation
                pitch = math.degrees(math.atan2(axis.z, math.hypot(axis.x, axis.y))-math.atan2(ref_axis.z, math.hypot(ref_axis.x,ref_axis.y)))
                sample[side] = {'foot': xyz(foot.translation), 'toe': xyz(toe.translation), 'pitch': round(pitch, 3)}
            samples.append(sample)
        data['clips'][key] = {'path': path, 'seconds': clip.get_play_length(),
            'markers': [{'name':str(m.marker_name),'time':m.time} for m in u.AnimationLibrary.get_animation_sync_markers(clip)],
            'samples':samples}
    report[label] = data
(OUT / 'source-trajectories.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('READ_GAIT_SOURCES_SAVED '+str(OUT / 'source-trajectories.json'))
