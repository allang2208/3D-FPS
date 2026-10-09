"""Read the installed quick-melee source keys for scoped left-arm authoring."""
import json
from pathlib import Path
import unreal as u

O = Path(__file__).parent
previous = json.loads((O / 'animation_patch.json').read_text())
inputs = json.loads((O / 'inputs.json').read_text())
mesh = u.load_asset(inputs['mesh'])
asset = u.load_asset(previous['melee_path'])
options = u.AnimPoseEvaluationOptions()
options.optional_skeletal_mesh = mesh
options.should_retarget = False
options.evaluation_type = u.AnimDataEvalType.SOURCE
def pack(t):
    return [*t.translation.to_tuple(), t.rotation.x, t.rotation.y, t.rotation.z,
            t.rotation.w, *t.scale3d.to_tuple()]
duration = asset.get_play_length()
fps = previous['fps']
frames = round(duration * fps)
times = [i / fps for i in range(frames + 1)]
rows = []
for t in times:
    pose = u.AnimPoseExtensions.get_anim_pose_at_time(asset, t, options)
    rows.append({n: pack(u.AnimPoseExtensions.get_bone_pose(pose, n, u.AnimPoseSpaces.LOCAL))
                 for n in inputs['names']})
data = dict(revision='Super90QuickMelee-InstalledBeforeLeftArmR5', duration=duration,
            fps=fps, frames=frames, melee_path=asset.get_path_name(),
            base_tracks=[dict(bone=n, times=times, values=[v for row in rows for v in row[n]])
                         for n in inputs['names']], profiles={})
for family, spec in previous['profiles'].items():
    profile = u.load_asset(spec['path'])
    for clip in profile.get_editor_property('clips'):
        if clip.get_editor_property('base') != asset:
            continue
        retained = clip.get_editor_property('retained')
        if retained:
            raise RuntimeError('Current melee uses retained animation: ' + family)
        data['profiles'][family] = dict(path=profile.get_path_name(), clip=dict(
            base=asset.get_path_name(), duration=float(clip.get_editor_property('duration')),
            tracks=[dict(bone=str(t.get_editor_property('bone')), times=list(t.get_editor_property('times')),
                         values=list(t.get_editor_property('values'))) for t in clip.get_editor_property('tracks')]))
(O / 'installed_source.json').write_text(json.dumps(data, separators=(',', ':')))
print('SUPER90_LEFT_ARM_SOURCE_READ', len(rows), 'frames', len(data['profiles']), 'profiles', flush=True)
