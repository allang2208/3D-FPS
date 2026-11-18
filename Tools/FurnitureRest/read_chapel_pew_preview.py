"""Read saved native pew clips and actual skin/furniture geometry. No asset writes."""
import json
import os
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = Path(os.environ.get('CHAPEL_PREVIEW_ROOT', str(ROOT / 'SourceAssets/ChapelFurniture20261116/PreviewR1')))
OUT.mkdir(parents=True, exist_ok=True)
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
body = read(ROOT / 'Content/ColdSteelData/player_body.json')
furniture = read(ROOT / 'Content/ColdSteelData/furniture_rest.json')
profile = next(p for p in furniture['furniture'] if any(s['kind'] == 'ChapelPew' for s in p['slots']))
G, B, Q, L = u.GeometryScript_AssetUtils, u.GeometryScript_BoneWeights, u.GeometryScript_MeshQueries, u.GeometryScript_List


def xyz(v):
    return [v.x, v.y, v.z]


def pack(t):
    return [*xyz(t.translation), t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w, *xyz(t.scale3d)]


def geometry(path, skeletal):
    asset = u.load_asset(path)
    copier = G.copy_mesh_from_skeletal_mesh if skeletal else G.copy_mesh_from_static_mesh
    dm, status = copier(asset, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot read preview geometry: ' + path)
    _, points, _ = Q.get_all_vertex_positions(dm, False)
    _, triangles, _ = Q.get_all_triangle_indices(dm, False)
    points, triangles = L.convert_vector_list_to_array(points), L.convert_triangle_list_to_array(triangles)
    result = {'source': path, 'positions': [xyz(v) for v in points], 'triangles': [xyz(t) for t in triangles]}
    if skeletal:
        _, bones = B.get_all_bones_info(dm)
        result['bones'] = [{'name': str(b.name), 'parent': b.parent_index, 'bind': pack(b.world_transform)} for b in bones]
        result['weights'] = []
        for i in range(len(points)):
            _, weights, valid = B.get_vertex_bone_weights(dm, i)
            if not valid:
                raise RuntimeError('Missing preview skin weights: ' + path)
            result['weights'].append([[w.bone_index, w.weight] for w in weights if w.weight > 0])
    return result


manifest = {'kind': 'saved_native_animation_preview', 'profile': profile,
            'type': furniture['types']['ChapelPew'], 'variants': {},
            'production_assets_modified': False, 'gameplay_recording': False}
for variant, node in (('default', body), ('kaitlin', body['body_variants']['kaitlin'])):
    folder = OUT / variant
    folder.mkdir(exist_ok=True)
    body_geo = geometry(node['body_mesh'], True)
    (folder / 'body.json').write_text(json.dumps(body_geo, separators=(',', ':')), encoding='utf-8')
    head_path = node['heads'][node['default_head']]['mesh']
    (folder / 'head.json').write_text(json.dumps(geometry(head_path, True), separators=(',', ':')), encoding='utf-8')
    mesh = u.load_asset(node['body_mesh'])
    names = [b['name'] for b in body_geo['bones']]
    opt = u.AnimPoseEvaluationOptions()
    opt.optional_skeletal_mesh = mesh
    opt.evaluation_type = u.AnimDataEvalType.COMPRESSED
    opt.should_retarget = False
    clips = {}
    for phase in ('Enter', 'Idle', 'Exit'):
        path = node['clips']['Rest.ChapelPew.' + phase]
        clip = u.load_asset(path)
        duration = clip.get_play_length()
        count = round(duration * 30) + 1
        frames = []
        for i in range(count):
            pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, i / 30, opt)
            frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose, n, u.AnimPoseSpaces.WORLD)) for n in names])
        clips[phase] = {'asset': path, 'duration': duration, 'rate': 30, 'world': frames}
        print('CHAPEL_PREVIEW_READ', variant, phase, flush=True)
    (folder / 'saved_poses.json').write_text(json.dumps({'mesh': node['body_mesh'], 'names': names, 'clips': clips}, separators=(',', ':')), encoding='utf-8')
    manifest['variants'][variant] = {'mesh': node['body_mesh'], 'head': head_path,
                                     'clips': {k: v['asset'] for k, v in clips.items()}}
    u.SystemLibrary.collect_garbage()
(OUT / 'pew.json').write_text(json.dumps(geometry(profile['mesh'], False), separators=(',', ':')), encoding='utf-8')
(OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print('CHAPEL_PREVIEW_READ_COMPLETE', flush=True)
