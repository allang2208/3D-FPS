"""Read source poses for the 201 underside support grasp; no playback or previews."""
import gzip
import hashlib
import json
import time
from pathlib import Path
import unreal as u

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
GL = PROJECT / 'SourceAssets/PKMLowpoly20260922/GripLayer56'
index = json.loads((GL / 'inputs.json').read_text())['201']
OUT = HERE / 'Inputs'
OUT.mkdir(exist_ok=True)
result_file = HERE / 'inputs.json'
result = json.loads(result_file.read_text()) if result_file.exists() else {'201': {}, 'donors': {}}
# This script only evaluates saved animation poses and writes external authoring data.

def pack(t):
    return [*t.translation.to_tuple(), t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w, *t.scale3d.to_tuple()]

def disk(key):
    return PROJECT / 'Content' / (key.split('.')[0].removeprefix('/Game/') + '.uasset')

started = time.time()
for key, old in index['clips'].items():
    if not ('/BeltFeed08/' in key or '/Animations/base/' in key):
        continue
    digest = hashlib.sha256(disk(key).read_bytes()).hexdigest()
    if key in result['201'] and result['201'][key]['sha256'] == digest:
        continue
    # The offline source set is after ArmHinge55b, before the reverted finger experiment.
    if old['sha256'] == digest and Path(old['file']).exists():
        result['201'][key] = old
        continue
    clip = u.load_asset(key)
    mesh = u.load_asset(index['mesh'])
    opts = u.AnimPoseEvaluationOptions()
    opts.optional_skeletal_mesh = mesh
    opts.evaluation_type = u.AnimDataEvalType.RAW
    times = [u.AnimationLibrary.get_time_at_frame(clip, f) for f in range(u.AnimationLibrary.get_num_frames(clip) + 1)]
    world = []
    for t in times:
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, t, opts)
        world.append([pack(u.AnimPoseExtensions.get_bone_pose(pose, n, u.AnimPoseSpaces.WORLD)) for n in index['bones']])
    filename = OUT / (key.rsplit('/', 1)[-1] + '.json.gz')
    with gzip.open(filename, 'wt', encoding='utf8') as f:
        json.dump({'asset': key, 'sha256': digest, 'times': times, 'bones': index['bones'], 'world': world,
                   'seconds': clip.get_play_length()}, f, separators=(',', ':'))
    result['201'][key] = {'file': str(filename), 'sha256': digest, 'keys': len(times), 'seconds': clip.get_play_length()}
    if time.time() - started > 15:
        break

donors = {
    'M4': ('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416', '/Game/Weapons/M4ContactImpactFinal/A_AKM_idle'),
    'SVD': ('/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/SK_SVD_ModularStock',
            '/Game/Weapons/SVDDragunov20260922/Complete20260923/Animations/A_SVD_idle'),
    'AKM': ('/Game/Weapons/AKMIntegration/SovietFab/SK_AKM_SovietFab', '/Game/Weapons/AKMIntegration/SourceMatched/A_AKM_idle'),
}
for name, (mesh_path, key) in donors.items():
    if name in result['donors']:
        continue
    if not u.EditorAssetLibrary.does_asset_exist(mesh_path):
        # Pose locals are read from the animation's native skeleton when a cosmetic mesh is absent.
        mesh_path = None
    clip = u.load_asset(key)
    if not clip:
        continue
    opts = u.AnimPoseEvaluationOptions()
    opts.optional_skeletal_mesh = u.load_asset(mesh_path) if mesh_path else None
    opts.evaluation_type = u.AnimDataEvalType.RAW
    pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, 0.0, opts)
    result['donors'][name] = {'asset': key, 'mesh': mesh_path,
        'world': {n: pack(u.AnimPoseExtensions.get_bone_pose(pose, n, u.AnimPoseSpaces.WORLD)) for n in index['bones']},
        'local': {n: pack(u.AnimPoseExtensions.get_bone_pose(pose, n, u.AnimPoseSpaces.LOCAL)) for n in index['bones']}}
result_file.write_text(json.dumps(result, indent=1))
print('SUPPORTGRASP_SOURCE_READ', len(result['201']), list(result['donors']), flush=True)
