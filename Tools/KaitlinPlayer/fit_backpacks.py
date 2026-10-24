"""Fit the four packs to female body/shirt surfaces, retaining rigid bag shapes."""
import copy
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from body_surface_fit import BodySurfaceFit, regions

WORK = Path('D:/FPS3D/FPSGAME/SourceAssets/KaitlinPlayer20261023')
INPUT, OUTPUT = WORK / 'FitInputs', WORK / 'Backpacks'
read = lambda path: json.loads(path.read_text(encoding='utf-8-sig'))
body, modular, captured = [read(INPUT / (name + '.json')) for name in ('player_body', 'modular_outfits', 'captured')]
load_source = lambda path: read(INPUT / captured[path]['file'])
male = load_source(modular['profiles'][body['body_mesh']]['native_bare_skin'])
female = read(WORK / 'NativeGeometry/MHC_Kaitlin_Body.json')
mapping = read(WORK / 'body_correspondence.json')['target_to_source_vertices']
fit = BodySurfaceFit(male, female, mapping)
masks = read(OUTPUT / 'motion_masks.json')
statics = read(OUTPUT / 'static_bodies.json') if (OUTPUT / 'static_bodies.json').exists() else {}
garments = read(WORK / 'WorldGarments/manifest.json')
source_bones = {row['name']: row for row in male['bones']}
target_bones = {row['name']: row for row in female['bones']}


def hulls(shirt):
    meshes = [female]
    if shirt:
        path = modular['items'][shirt]['rig_meshes']['Jason']
        garment = read(Path(garments[path]['geometry']))
        meshes.append(dict(garment, bones=female['bones']))
    cloud = np.vstack([np.asarray(mesh['positions'])[regions(mesh) == 'torso'] for mesh in meshes])
    low = target_bones['pelvis']['position'][2]
    high = target_bones['neck_01']['position'][2] + 2.
    # Six overlapping bounded torso sections, as used by the existing sling.
    edges = np.linspace(low, high, 7)
    angles = np.arange(12) * (2. * np.pi / 12)
    normals = np.c_[np.cos(angles), np.sin(angles), np.zeros(12)]
    result, world = [], []
    for a, b in zip(edges[:-1], edges[1:]):
        a, b = a - .5, b + .5
        samples = cloud[(cloud[:, 2] >= a) & (cloud[:, 2] <= b)]
        if len(samples) < 4:
            raise RuntimeError('Incomplete female torso authoring section for ' + str(shirt))
        planes = np.vstack([np.c_[normals, -(samples @ normals.T).max(axis=0) - .1],
                            [0., 0., -1., a], [0., 0., 1., -b]])
        name = min(('pelvis', 'spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05'),
                   key=lambda name: abs(target_bones[name]['position'][2] - (a + b) * .5))
        bone = target_bones[name]
        local_normals = planes[:, :3] @ np.asarray(bone['axes']).T
        local_distance = planes[:, 3] + planes[:, :3] @ bone['position']
        lengths = np.linalg.norm(local_normals, axis=1)
        local_planes = np.c_[local_normals, local_distance] / lengths[:, None]
        result.append({'bone': name, 'side_planes': 12, 'planes': local_planes.tolist()})
        world.append(planes)
    return result, world


def rear_shift(points, sections, gap=.3):
    penetrations = []
    for planes in sections:
        local = points[(points[:, 2] >= planes[-2, 3]) & (points[:, 2] <= -planes[-1, 3])]
        if not len(local):
            continue
        side = planes[:12]
        lower = np.full(len(local), -np.inf)
        upper = np.full(len(local), np.inf)
        valid = np.ones(len(local), bool)
        for x, y, z, d in side:
            offset = x * local[:, 0] + z * local[:, 2] + d
            if y < -.01:
                lower = np.maximum(lower, -offset / y)
            elif y > .01:
                upper = np.minimum(upper, -offset / y)
            else:
                valid &= offset <= 0
        valid &= lower <= upper
        if np.any(valid):
            penetrations.append(np.max(local[valid, 1] - lower[valid] + gap))
    if not penetrations:
        raise RuntimeError('The pack has no authored torso contact region.')
    return -max(penetrations)


def move_anchor(point, weights):
    data = {'positions': [np.asarray(point).tolist()], 'weights': [weights], 'bones': male['bones'],
            'source': male['source'], 'materials': []}
    return np.asarray(fit.garment(data)['positions'][0])


manifest = read(OUTPUT / 'manifest.json') if (OUTPUT / 'manifest.json').exists() else {}
mounts = read(OUTPUT / 'mounts.json') if (OUTPUT / 'mounts.json').exists() else {}
source_frame, target_frame = source_bones['spine_04'], target_bones['spine_04']
rotation = np.linalg.inv(source_frame['axes']) @ np.asarray(target_frame['axes'])
base_translation = np.asarray(target_frame['position']) - np.asarray(source_frame['position']) @ rotation
for item, original_mount in body['outfits'].items():
    mount = copy.deepcopy(original_mount)
    variants = {'': original_mount['world_mesh'], **original_mount['world_mesh_by_shirt']}
    if item in mounts and all(path in manifest for path in variants.values()):
        continue
    all_bounds, shifts = [], {}
    for shirt, path in variants.items():
        source = load_source(path)
        positions = np.asarray(source['positions'])
        mask = np.asarray(masks[path])
        surface = fit.garment(source)
        fixed = np.asarray(surface['positions'])
        collision, sections = hulls(shirt)
        translation = base_translation.copy()
        rigid = positions @ rotation + translation
        if 'rigid_pack' in mount:
            original_location = original_mount['rigid_pack'].get('location_by_shirt', {}).get(shirt, original_mount['rigid_pack']['location'])
            if 'hanging_pack' in original_mount:
                hanging = original_mount.get('hanging_pack_by_shirt', {}).get(shirt, original_mount['hanging_pack'])
                contacts = np.asarray(hanging['probes']) @ rotation + translation
            else:
                raw_body = np.asarray(statics[original_mount['rigid_pack']['mesh']]['positions'])
                original_rotation = Rotation.from_quat(original_mount['rigid_pack']['rotation_quat']).as_matrix()
                static_body = raw_body @ original_rotation.T + original_location
                contacts = static_body @ rotation + translation
        else:
            # Bag surfaces and their sewn ends have a full rigid motion mask.
            contacts = rigid[mask >= .999]
        translation[1] += rear_shift(contacts, sections)
        rigid = positions @ rotation + translation
        fitted = fixed * (1. - mask[:, None]) + rigid * mask[:, None]
        surface['positions'] = fitted.tolist()
        surface['source_sha256'] = source['source_sha256']
        surface['method'] = 'native_surface_harness_and_rigid_pack_with_shared_sewn_ends'
        digest = hashlib.sha256(path.encode()).hexdigest()[:10]
        asset = '/Game/Characters/ModularOutfit20260924/KaitlinPlayer20261023/Backpacks/SK_Kaitlin_' + item + '_' + digest
        file = OUTPUT / (digest + '.json')
        file.write_text(json.dumps(surface, separators=(',', ':')), encoding='utf-8')
        manifest[path] = {'geometry': str(file), 'asset': asset, 'source_sha256': source['source_sha256']}
        target_path = asset + '.' + asset.rsplit('/', 1)[-1]
        if shirt:
            mount['world_mesh_by_shirt'][shirt] = target_path
        else:
            mount['world_mesh'] = target_path
        shifts[shirt] = translation
        moving = rigid[mask >= .999]
        all_bounds.append((moving.min(axis=0), moving.max(axis=0)))
        if 'rigid_pack' in mount:
            location = np.asarray(original_location) @ rotation + translation
            if shirt:
                mount['rigid_pack']['location_by_shirt'][shirt] = location.tolist()
            else:
                mount['rigid_pack']['location'] = location.tolist()
            pack_rotation = Rotation.from_matrix(rotation.T) * Rotation.from_quat(original_mount['rigid_pack']['rotation_quat'])
            mount['rigid_pack']['rotation_quat'] = pack_rotation.as_quat().tolist()
            if 'hanging_pack' not in original_mount:
                moving_body = static_body @ rotation + translation
                all_bounds[-1] = (moving_body.min(axis=0), moving_body.max(axis=0))
                print('KAITLIN_PACK_AUTHORED', item, shirt or 'bare', flush=True)
                continue
            result = copy.deepcopy(hanging)
            result['center'] = location.tolist()
            result['probes'] = (np.asarray(hanging['probes']) @ rotation + translation).tolist()
            result['hulls'] = collision
            lo, hi = [original_mount['backpack_motion'][key] for key in ('bounds_min', 'bounds_max')]
            corners = np.asarray([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
            corners = corners @ rotation + translation
            all_bounds[-1] = (corners.min(axis=0), corners.max(axis=0))
            for old, new in zip(hanging['tethers'], result['tethers']):
                new['point'] = (np.asarray(old['point']) @ rotation + translation).tolist()
                original_support, fitted_support = np.zeros(3), np.zeros(3)
                for old_binding, new_binding in zip(old['support'], new['support']):
                    name, weight = old_binding['bone'], old_binding['weight']
                    sb, tb = source_bones[name], target_bones[name]
                    point = np.asarray(old_binding['local']) @ sb['axes'] + sb['position']
                    moved = move_anchor(point, [[sb['index'], 1.]])
                    new_binding['local'] = ((moved - tb['position']) @ np.linalg.inv(tb['axes'])).tolist()
                    original_support += point * weight
                    fitted_support += moved * weight
                slack = max(0., old['length'] - np.linalg.norm(np.asarray(old['point']) - original_support))
                new['length'] = float(np.linalg.norm(np.asarray(new['point']) - fitted_support) + slack)
            if shirt:
                mount['hanging_pack_by_shirt'][shirt] = result
            else:
                mount['hanging_pack'] = result
        print('KAITLIN_PACK_AUTHORED', item, shirt or 'bare', flush=True)
    motion = mount['backpack_motion']
    motion['pivot'] = (np.asarray(original_mount['backpack_motion']['pivot']) @ rotation + shifts['']).tolist()
    motion['bounds_min'] = np.min([a for a, b in all_bounds], axis=0).tolist()
    motion['bounds_max'] = np.max([b for a, b in all_bounds], axis=0).tolist()
    mounts[item] = mount
(OUTPUT / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
(OUTPUT / 'mounts.json').write_text(json.dumps(mounts, indent=2), encoding='utf-8')
print('KAITLIN_PACKS_AUTHORED', len(manifest), flush=True)
