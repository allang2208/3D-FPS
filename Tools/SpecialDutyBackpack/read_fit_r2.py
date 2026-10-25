"""Capture the saved bodies, shirts and actual waist routes for this repair only."""
import gc
import hashlib
import json
from pathlib import Path
import unreal as u

P = Path('D:/FPS3D/FPSGAME')
R = P / 'SourceAssets/SpecialDutyBackpack20261024/MeshyFitR1_20261024'
OUT = R / 'BodyInputs'
OUT.mkdir(parents=True, exist_ok=True)
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
body = read(P / 'Content/ColdSteelData/player_body.json')
modular = read(P / 'Content/ColdSteelData/modular_outfits.json')
G, Q, L, B = u.GeometryScript_AssetUtils, u.GeometryScript_MeshQueries, u.GeometryScript_List, u.GeometryScript_BoneWeights
vec = lambda v: [v.x, v.y, v.z]
records = []
cache = {}

def capture(path, weighted):
    if (path, weighted) in cache:
        return cache[path, weighted]
    filename = hashlib.sha256((path + str(weighted)).encode()).hexdigest()[:16] + '.json'
    package = P / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')
    cached = OUT / filename
    if cached.exists() and package.stat().st_mtime_ns <= cached.stat().st_mtime_ns:
        data = read(cached)
        if data.get('source') == path:
            records.append({'source':path,'file':filename,'weighted':weighted,
                            'package_sha256':hashlib.sha256(package.read_bytes()).hexdigest(),
                            'vertices':len(data.get('positions',data.get('points',[]))),
                            'resumed_saved_snapshot':True})
            cache[path, weighted] = filename
            return filename
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError('Missing fit input ' + path)
    dm, status = G.copy_mesh_from_skeletal_mesh(asset, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot read fit input ' + path)
    _, points, _ = Q.get_all_vertex_positions(dm, False)
    points = [vec(v) for v in L.convert_vector_list_to_array(points)]
    if weighted:
        _, faces, _ = Q.get_all_triangle_indices(dm, False)
        _, bones = B.get_all_bones_info(dm)
        faces = [vec(t) for t in L.convert_triangle_list_to_array(faces)]
        data = {'source': path, 'positions': points, 'triangles': faces,
                'materials': [{'slot': str(m.material_slot_name), 'asset': m.material_interface.get_path_name() if m.material_interface else None} for m in asset.materials],
                'triangle_materials': [u.GeometryScript_Materials.get_triangle_material_id(dm, i)[0] for i in range(len(faces))],
                'bones': [{'index': b.index, 'name': str(b.name), 'parent': b.parent_index} for b in bones],
                'reference': {str(b.name): vec(b.world_transform.translation) + [getattr(b.world_transform.rotation, c) for c in 'xyzw'] + vec(b.world_transform.scale3d) for b in bones}, 'weights': []}
        for i in range(len(points)):
            _, pairs, valid = B.get_vertex_bone_weights(dm, i)
            if not valid:
                raise RuntimeError('Missing native weights ' + path)
            data['weights'].append([[w.bone_index, w.weight] for w in pairs if w.weight > 0])
    else:
        # Only torso/waist samples are needed; no change to the clothes themselves.
        data = {'source': path, 'points': [v for v in points if abs(v[0]) < 28 and 80 < v[2] < 151]}
    filename = hashlib.sha256((path + str(weighted)).encode()).hexdigest()[:16] + '.json'
    (OUT / filename).write_text(json.dumps(data, separators=(',', ':')))
    package = P / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')
    row = {'source': path, 'file': filename, 'weighted': weighted,
           'package_sha256': hashlib.sha256(package.read_bytes()).hexdigest(), 'vertices': len(points)}
    records.append(row)
    cache[path, weighted] = filename
    del dm, asset, data, points
    gc.collect()
    u.SystemLibrary.collect_garbage()
    print('PATHFINDER_FIT_CAPTURED', path, flush=True)
    return filename

rigs = {}
for rig, config, items in [('Jason', body, modular['items']), ('Kaitlin', body['body_variants']['kaitlin'], modular['body_variants']['kaitlin']['items'])]:
    pack = config['outfits']['ue_pathfinder_backpack']
    row = {'body': capture(config['body_mesh'], True), 'shirts': {}, 'waist_routes': [], 'template': pack['world_mesh']}
    for key in pack['world_mesh_by_shirt']:
        item = items[key]
        path = item['rig_meshes'][rig]
        entry = {'base': capture(path, True), 'surfaces': []}
        # Include every selected world shirt route, including the default tucked layer.
        paths = {path}
        for field in ('pants_mesh_fit_meshes', 'pants_fit_meshes'):
            for fit in item.get(field, {}).values():
                if rig in fit.get('rig_meshes', {}):
                    paths.add(fit['rig_meshes'][rig])
        fallback = item.get('pants_fit_default', {}).get('rig_meshes', {}).get(rig)
        if fallback:
            paths.add(fallback)
        for path in sorted(paths):
            entry['surfaces'].append(capture(path, False))
        row['shirts'][key] = entry
    for key, item in items.items():
        if item.get('slot') != 15:
            continue
        paths = {item['rig_meshes'][rig]}
        for fit in item.get('shoe_fit_meshes', {}).values():
            if rig in fit:
                paths.add(fit[rig])
        for path in sorted(paths):
            row['waist_routes'].append({'item': key, 'source': path, 'file': capture(path, False)})
    rigs[rig] = row
    (OUT / 'capture_progress.json').write_text(json.dumps({'rigs': rigs, 'records': records}, indent=2))
(OUT / 'manifest.json').write_text(json.dumps({'rigs': rigs, 'records': records}, indent=2))
print('PATHFINDER_FIT_INPUTS_COMPLETE', len(records), flush=True)
