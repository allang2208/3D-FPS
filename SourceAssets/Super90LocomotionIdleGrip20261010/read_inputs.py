"""Read installed idle and locomotion authoring inputs; no gameplay run."""
import json
from pathlib import Path
import unreal as u

O = Path(__file__).parent
BASE = '/Game/Weapons/Super90/Cransh20261006/Animations/A_Super90_'
mesh = u.load_asset('/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7')
component = u.SkeletalMeshComponent()
component.set_skeletal_mesh_asset(mesh)
names = [str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
parents = {n: str(component.get_parent_bone(n)) for n in names}
options = u.AnimPoseEvaluationOptions()
options.optional_skeletal_mesh = mesh
options.should_retarget = False
options.evaluation_type = u.AnimDataEvalType.SOURCE


def sample(asset, time):
    pose = u.AnimPoseExtensions.get_anim_pose_at_time(asset, time, options)
    out = {}
    for n in names:
        t = u.AnimPoseExtensions.get_bone_pose(pose, n, u.AnimPoseSpaces.LOCAL)
        out[n] = [*t.translation.to_tuple(), t.rotation.x, t.rotation.y, t.rotation.z,
                  t.rotation.w, *t.scale3d.to_tuple()]
    return out


data = dict(names=names, parents=parents, clips={}, profiles={}, runtime_tested=False)
for role in ('idle', 'walk', 'run'):
    asset = u.load_asset(BASE + role)
    if not asset:
        raise RuntimeError('Missing installed clip: ' + role)
    duration = asset.get_play_length()
    frames = u.AnimationLibrary.get_num_frames(asset)
    times = [0.] if role == 'idle' else [i * duration / frames for i in range(frames + 1)]
    data['clips'][role] = dict(path=asset.get_path_name(), duration=duration, frames=frames,
                               times=times, rows=[sample(asset, t) for t in times])
paths = {c['path'] for c in data['clips'].values()}
for family in ('vertical', 'canted', 'prism', 'angled'):
    asset = u.load_asset('/Game/Weapons/Super90/Foregrips20261007/Profiles/DA_Super90_' + family)
    if not asset:
        raise RuntimeError('Missing installed profile: ' + family)
    clips = {}
    for c in asset.get_editor_property('clips'):
        path = c.get_editor_property('base').get_path_name()
        if path not in paths:
            continue
        retained = c.get_editor_property('retained')
        if retained:
            raise RuntimeError('Preserve retained animation: ' + retained.get_path_name())
        clips[path] = dict(base=path, duration=float(c.get_editor_property('duration')),
            tracks=[dict(bone=str(t.get_editor_property('bone')), times=list(t.get_editor_property('times')),
                         values=list(t.get_editor_property('values'))) for t in c.get_editor_property('tracks')])
    if set(clips) != paths:
        raise RuntimeError('Missing idle/locomotion profile entry: ' + family)
    data['profiles'][family] = dict(path=asset.get_path_name(), clips=clips)
(O / 'inputs.json').write_text(json.dumps(data, separators=(',', ':')))
print('SUPER90_LOCOMOTION_INPUTS', {k: (c['frames'], c['duration']) for k, c in data['clips'].items()}, '4 profiles', flush=True)
