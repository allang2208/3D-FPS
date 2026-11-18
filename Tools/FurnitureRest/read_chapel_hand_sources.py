"""Capture current pew motion and native relaxed-sofa references for hand fitting."""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/ChapelFurniture20261116/HandsR2'
OUT.mkdir(parents=True, exist_ok=True)
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
body = read(ROOT / 'Content/ColdSteelData/player_body.json')
result = {}


def pack(t):
    return [t.translation.x, t.translation.y, t.translation.z,
            t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w,
            t.scale3d.x, t.scale3d.y, t.scale3d.z]


for variant, node in (('default', body), ('kaitlin', body['body_variants']['kaitlin'])):
    mesh = u.load_asset(node['body_mesh'])
    ref = mesh.skeleton.get_reference_pose()
    names = [str(n) for n in u.AnimPoseExtensions.get_bone_names(ref)]
    comp = u.new_object(u.SkeletalMeshComponent)
    comp.set_skeletal_mesh_asset(mesh)
    index = {n: i for i, n in enumerate(names)}
    data = {'mesh': node['body_mesh'], 'names': names,
            'parents': [index.get(str(comp.get_parent_bone(n)), -1) for n in names],
            'reference': [pack(u.AnimPoseExtensions.get_bone_pose(ref, n, u.AnimPoseSpaces.LOCAL)) for n in names],
            'clips': {}, 'references': {}}
    options = u.AnimPoseEvaluationOptions()
    options.optional_skeletal_mesh = mesh
    options.evaluation_type = u.AnimDataEvalType.COMPRESSED
    options.should_retarget = False
    for family, group in (('ChapelPew', data['clips']), ('Sofa', data['references'])):
        for phase in ('Enter', 'Idle', 'Exit'):
            path = node['clips']['Rest.' + family + '.' + phase]
            clip = u.load_asset(path)
            duration = clip.get_play_length()
            frames = []
            for i in range(round(duration * 30) + 1):
                pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, i / 30, options)
                frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose, n, u.AnimPoseSpaces.LOCAL)) for n in names])
            group[phase] = {'asset': path, 'duration': duration, 'rate': 30, 'frames': frames}
            print('CHAPEL_HAND_SOURCE', variant, family, phase, flush=True)
    result[variant] = data
(OUT / 'native_sources.json').write_text(json.dumps(result, separators=(',', ':')), encoding='utf-8')
print('CHAPEL_HAND_SOURCES_CAPTURED', flush=True)
