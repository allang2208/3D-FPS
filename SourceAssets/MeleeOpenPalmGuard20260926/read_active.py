"""Read only the active guard families needed to author their replacement."""
import hashlib
import json
from pathlib import Path
import unreal as u

P = Path(__file__).parent
ROOT = Path(u.Paths.project_dir()).resolve()
families = {
    'Standard': ('/Game/Weapons/AzureRunesword20260913',
                 '/Game/Weapons/AzureRunesword20260913/Modules20260919/SK_RuneSword_Arms'),
    'LongGrip': ('/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations',
                 '/Game/Weapons/FrostCrystalSword20260915/Modules20260915/SK_FrostSword_Arms'),
}
def pack(t):
    p, q, s = t.translation, t.rotation, t.scale3d
    return {'p': [p.x, p.y, p.z], 'q': [q.w, q.x, q.y, q.z], 's': [s.x, s.y, s.z]}

for variant, (folder, mesh_path) in families.items():
    mesh = u.load_asset(mesh_path)
    component = u.SkeletalMeshComponent()
    component.set_skeletal_mesh_asset(mesh)
    names = [str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
    parents = {n: str(component.get_parent_bone(n)) for n in names}
    options = u.AnimPoseEvaluationOptions()
    options.evaluation_type = u.AnimDataEvalType.SOURCE
    options.optional_skeletal_mesh = mesh
    data = {'variant': variant, 'mesh': mesh_path, 'bones': names, 'parents': parents, 'clips': {}}
    reference = u.AnimPoseExtensions.get_reference_pose(mesh.skeleton)
    data['reference'] = {n: pack(u.AnimPoseExtensions.get_bone_pose(reference, n, u.AnimPoseSpaces.WORLD)) for n in names}
    for clip in ('Idle', 'Guard', 'GuardHit', 'GuardBreak'):
        asset_path = folder + '/A_RuneSword_' + clip
        asset = u.load_asset(asset_path)
        intervals = u.AnimationLibrary.get_num_frames(asset)
        seconds = asset.get_play_length()
        disk = ROOT / 'Content' / (asset_path.removeprefix('/Game/') + '.uasset')
        info = {'asset': asset_path, 'source_sha256': hashlib.sha256(disk.read_bytes()).hexdigest(),
                'intervals': intervals, 'seconds': seconds, 'samples': []}
        for index in ([0] if clip == 'Idle' else range(intervals + 1)):
            t = seconds * index / max(1, intervals)
            pose = u.AnimPoseExtensions.get_anim_pose_at_time(asset, t, options)
            info['samples'].append({'seconds': t, 'world': {
                n: pack(u.AnimPoseExtensions.get_bone_pose(pose, n, u.AnimPoseSpaces.WORLD)) for n in names}})
        data['clips'][clip] = info
    (P / (variant + '_active.json')).write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
    print('GUARD_AUTHOR_INPUTS ' + variant + ' ' + json.dumps({k: v['intervals'] for k, v in data['clips'].items()}))
