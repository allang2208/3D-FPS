"""Read source poses used to author wolf combat timing; no playback or rendering."""
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/WolfMonster'
OUT.mkdir(parents=True, exist_ok=True)
mesh = u.load_asset('/Game/AnimalVarietyPack/Wolf/Meshes/SK_Wolf')
options = u.AnimPoseEvaluationOptions()
options.set_editor_property('evaluation_type', u.AnimDataEvalType.SOURCE)
options.set_editor_property('optional_skeletal_mesh', mesh)
bounds = mesh.get_bounds()
def xyz(v):
    return [round(v.x, 5), round(v.y, 5), round(v.z, 5)]

report = {'bounds_origin': xyz(bounds.origin), 'bounds_extent': xyz(bounds.box_extent),
          'basis': 'source component-space bone samples; no visual acceptance', 'clips': {}}
for role in ['Bite', 'JumpBite', 'Walk_RM', 'Run_RM', 'Death', 'GetHitFront', 'GetHitLeft', 'GetHitRight']:
    clip = u.load_asset('/Game/AnimalVarietyPack/Wolf/Animations/ANIM_Wolf_' + role)
    frames = u.AnimationLibrary.get_num_frames(clip)
    rows = []
    for frame in range(frames + 1):
        time = frame * clip.get_play_length() / frames
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, time, options)
        row = {'frame': frame, 'seconds': time, 'bones': {}}
        for bone in ['root', 'Wolf_', 'Wolf_-Pelvis', 'Wolf_-Head', 'Wolf_-Ponytail1',
                     'Wolf_-L-Hand', 'Wolf_-R-Hand', 'Wolf_-L-Foot', 'Wolf_-R-Foot']:
            transform = u.AnimPoseExtensions.get_bone_pose(pose, bone, u.AnimPoseSpaces.WORLD)
            row['bones'][bone] = xyz(transform.translation)
        rows.append(row)
    report['clips'][role] = {'seconds': clip.get_play_length(), 'frame_intervals': frames, 'samples': rows}
(OUT / 'reference_motion.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
u.log('WOLF_REFERENCE_MOTION_WRITTEN')
