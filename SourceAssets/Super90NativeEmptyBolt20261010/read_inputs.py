"""Read the installed ordinary empty-reload tail and existing bolt action."""
import json
from pathlib import Path
import unreal as u
O = Path(__file__).parent
paths = {
    'idle': '/Game/Weapons/Super90/Cransh20261006/Animations/A_Super90_idle',
    'empty': '/Game/Weapons/Super90/Cransh20261006/Animations/A_Super90_reload_full',
    'cycle': '/Game/Weapons/Super90/Speedloader20261007/Animations/A_Super90_loader_cycle'}
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
    p = u.AnimPoseExtensions.get_anim_pose_at_time(asset, time, options)
    out = {}
    for n in names:
        t = u.AnimPoseExtensions.get_bone_pose(p, n, u.AnimPoseSpaces.LOCAL)
        out[n] = [*t.translation.to_tuple(), t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w, *t.scale3d.to_tuple()]
    return out

data = dict(names=names, parents=parents, clips={}, profiles={}, runtime_tested=False)
for role, path in paths.items():
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError('Missing ' + path)
    duration, frames = asset.get_play_length(), u.AnimationLibrary.get_num_frames(asset)
    times = [0.] if role == 'idle' else [i * duration / frames for i in range(frames + 1)]
    data['clips'][role] = dict(path=asset.get_path_name(), duration=duration, frames=frames, times=times,
                               rows=[sample(asset, t) for t in times])
for family in ('vertical', 'canted', 'prism', 'angled'):
    asset = u.load_asset('/Game/Weapons/Super90/Foregrips20261007/Profiles/DA_Super90_' + family)
    clips = {}
    for c in asset.get_editor_property('clips'):
        path = c.get_editor_property('base').get_path_name()
        if path not in {d['path'] for d in data['clips'].values()}:
            continue
        retained = c.get_editor_property('retained')
        if retained:
            raise RuntimeError('Preserve retained clip ' + path)
        clips[path] = dict(base=path, duration=float(c.get_editor_property('duration')),
            tracks=[dict(bone=str(t.get_editor_property('bone')), times=list(t.get_editor_property('times')),
                values=list(t.get_editor_property('values'))) for t in c.get_editor_property('tracks')])
    data['profiles'][family] = dict(path=asset.get_path_name(), clips=clips)
(O / 'inputs.json').write_text(json.dumps(data, separators=(',', ':')))
print('SUPER90_NATIVE_EMPTY_INPUTS', {k: (v['frames'], v['duration']) for k, v in data['clips'].items()}, flush=True)
