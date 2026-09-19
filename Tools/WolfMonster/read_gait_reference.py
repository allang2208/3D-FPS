"""Read the requested Godot/UE source motion reference; no game or acceptance run."""
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/QuadrupedTemplates/LocomotionV2'
OUT.mkdir(parents=True, exist_ok=True)
legacy = Path('E:/3d/trash/repository-ue5-root-20260910')
gltf = json.loads((legacy / 'assets/models/wolf_quaternius.gltf').read_text(encoding='utf-8'))
report = {
    'legacy_project': str(legacy),
    'legacy_runtime_model': 'assets/models/wolf_quaternius.gltf',
    'legacy_runtime_driver': 'scripts/wolf_anim.gd',
    'legacy_reference_viewed': ['tools/ai-gen/black-wolf-fur-v01-20260906/Gallop-frames-0.jpg',
                                'tools/ai-gen/black-wolf-fur-v01-20260906/Gallop-frames-1.jpg'],
    'legacy_movement': 'moving selects full Gallop at speed_scale=1; main.gd bob=0; the unused procedural WolfRig is not this active motion',
    'legacy_clips': {}, 'ue_clips': {},
    'basis': 'existing source motion reference; no post-change runtime or visual acceptance',
}
for clip in gltf['animations']:
    if clip['name'] not in ('Gallop', 'Walk'):
        continue
    inputs = [gltf['accessors'][sampler['input']] for sampler in clip['samplers']]
    report['legacy_clips'][clip['name']] = {
        'seconds': max(row['max'][0] for row in inputs),
        'maximum_keys': max(row['count'] for row in inputs),
        'channels': len(clip['channels']),
    }
mesh = u.load_asset('/Game/AnimalVarietyPack/Wolf/Meshes/SK_Wolf')
options = u.AnimPoseEvaluationOptions()
options.set_editor_property('evaluation_type', u.AnimDataEvalType.SOURCE)
options.set_editor_property('optional_skeletal_mesh', mesh)
for role in ['Walk', 'Run', 'WalkTurnL', 'WalkTurnR', 'RunTurnL', 'RunTurnR']:
    clip = u.load_asset('/Game/AnimalVarietyPack/Wolf/Animations/ANIM_Wolf_' + role)
    row = {'seconds': clip.get_play_length(), 'intervals': u.AnimationLibrary.get_num_frames(clip), 'samples': []}
    for phase in [0., .25, .5, .75]:
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, phase * clip.get_play_length(), options)
        sample = {'phase': phase, 'bones': {}}
        for bone in ['root', 'Wolf_', 'Wolf_-Pelvis', 'Wolf_-Spine', 'Wolf_-Spine1', 'Wolf_-Head',
                     'Wolf_-L-Hand', 'Wolf_-R-Hand', 'Wolf_-L-Foot', 'Wolf_-R-Foot']:
            t = u.AnimPoseExtensions.get_bone_pose(pose, bone, u.AnimPoseSpaces.WORLD)
            sample['bones'][bone] = [round(t.translation.x, 4), round(t.translation.y, 4), round(t.translation.z, 4)]
        row['samples'].append(sample)
    report['ue_clips'][role] = row
    u.log('WOLF_GAIT_REFERENCE ' + role + ' seconds=' + str(row['seconds']) + ' head=' + str(row['samples'][0]['bones']['Wolf_-Head']))
(OUT / 'source_reference.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
u.log('WOLF_GAIT_REFERENCE_WRITTEN')
