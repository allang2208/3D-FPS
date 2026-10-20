"""Read the installed loader clips and their four grip deltas for R26 authoring."""
import json, hashlib
from pathlib import Path
import unreal as u
O = Path(__file__).parent
P = O.parents[1]
root = '/Game/Weapons/Super90/Speedloader20261007/Animations/'
paths = {branch + '_' + str(i): root + 'A_Super90_loader_' + branch + '_' + str(i) for branch in ('normal', 'empty') for i in range(1, 8)}

mesh = u.load_asset('/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7')
component = u.SkeletalMeshComponent()
component.set_skeletal_mesh_asset(mesh)
names = [str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
parents = {n: str(component.get_parent_bone(n)) for n in names}
options = u.AnimPoseEvaluationOptions()
options.optional_skeletal_mesh = mesh
options.should_retarget = False
options.evaluation_type = u.AnimDataEvalType.SOURCE
def sha(path):
    return hashlib.sha256((P / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')).read_bytes()).hexdigest()
def sample(asset, time):
    pose = u.AnimPoseExtensions.get_anim_pose_at_time(asset, time, options)
    row = {}
    for name in names:
        t = u.AnimPoseExtensions.get_bone_pose(pose, name, u.AnimPoseSpaces.LOCAL)
        row[name] = [*t.translation.to_tuple(), t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w, *t.scale3d.to_tuple()]
    return row
data = {'names': names, 'parents': parents, 'clips': {}, 'profiles': {}}
for role, path in paths.items():
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError('Missing ' + path)
    frames = u.AnimationLibrary.get_num_frames(asset)
    duration = asset.get_play_length()
    times = [i * duration / frames for i in range(frames + 1)]
    data['clips'][role] = {'path': asset.get_path_name(), 'sha256': sha(path),
        'duration': duration, 'frames': frames, 'start_frame': 0,
        'times': times, 'rows': [sample(asset, time) for time in times]}
    print('SUPER90_R26_INPUT', role, frames, flush=True)
for family in ('vertical', 'canted', 'prism', 'angled'):
    path = '/Game/Weapons/Super90/Foregrips20261007/Profiles/DA_Super90_' + family
    asset = u.load_asset(path)
    clips = {}
    for c in asset.get_editor_property('clips'):
        base = c.get_editor_property('base').get_path_name()
        if base not in {v['path'] for v in data['clips'].values()}:
            continue
        if c.get_editor_property('retained'):
            raise RuntimeError('Preserve retained loader clip ' + base)
        clips[base] = {'base': base, 'duration': float(c.get_editor_property('duration')),
            'tracks': [{'bone': str(t.get_editor_property('bone')), 'times': list(t.get_editor_property('times')),
                        'values': list(t.get_editor_property('values'))} for t in c.get_editor_property('tracks')]}
    data['profiles'][family] = {'path': asset.get_path_name(), 'sha256': sha(path), 'clips': clips}
(O / 'inputs.json').write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
print('SUPER90_R26_INPUTS_SAVED', len(data['clips']), flush=True)
