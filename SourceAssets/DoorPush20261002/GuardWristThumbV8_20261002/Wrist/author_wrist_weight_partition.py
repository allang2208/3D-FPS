"""Remove the thumb's erroneous influence on the wrist/palm heel only.

This production does not scale, smooth, move, or rebind the hand.  Native
reference bones and every surface attribute remain unchanged.  The accepted
V7 surface has a broad thumb_01 envelope reaching several centimetres behind
the wrist.  The guard's moving thumb pulls that envelope into a star fold.
Redistribute only the proximal spill to the unchanged hand_l carrier, retaining
the authored thumb weights at and beyond its own root joint.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PROJECT = Path('D:/FPS3D/FPSGAME')
PREVIOUS = PROJECT / 'SourceAssets/M16SprintDoorWrist20261002/Wrist'
CANONICAL = PROJECT / 'SourceAssets/ModularOutfit20260925/BarePalmV7/M4_original.json'
OUT = HERE / 'Authored'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def package(source):
    return PROJECT / 'Content' / (source.split('.')[0].removeprefix('/Game/') + '.uasset')


def matrix(bone):
    m = np.eye(4)
    m[:3, :3] = np.asarray(bone['axes']).T
    m[:3, 3] = bone['position']
    return m


def partition(weights, longitudinal_cm, thumb_root_cm):
    # The wrist boundary is hand_l's joint, not a screen-space width.  A
    # continuously differentiable transition reaches the original envelope at
    # the actual thumb root.  Real thumb-root and distal skin stays untouched.
    proximal_boundary = -.5
    t = np.clip((longitudinal_cm - proximal_boundary) /
                (thumb_root_cm - proximal_boundary), 0., 1.)
    retention = float(t * t * (3. - 2. * t))
    if retention >= 1.:
        return None
    thumb_names = [n for n, w in weights.items()
                   if n.startswith('thumb_') and n.endswith('_l') and w > 0]
    transferred = sum(weights[n] * (1. - retention) for n in thumb_names)
    if transferred <= 1e-8:
        return None
    target = dict(weights)
    for name in thumb_names:
        value = weights[name] * retention
        if value > 1e-9:
            target[name] = value
        else:
            target.pop(name)
    target['hand_l'] = target.get('hand_l', 0.) + transferred
    return target, transferred, retention


def main():
    old_manifest = read(PREVIOUS / 'Authored/authoring.json')
    installed = read(PREVIOUS / 'installed.json')
    reference = read(PREVIOUS / 'Authored/left_wrist_reference.json')['bones']
    common = read(CANONICAL)['bones']
    transfers = {n: matrix(reference[n]) @ np.linalg.inv(matrix(b))
                 for n, b in common.items() if n in reference}
    inverse_hand = np.linalg.inv(matrix(common['hand_l']))
    thumb_root = (inverse_hand @ np.r_[common['thumb_01_l']['position'], 1.])[0] * 100.
    # Bone matrices include the historical root scale of 100.  The result of
    # inverse_hand is metres, so canonical anatomical distances are in cm here.
    entries = []
    evidence = []
    for old in old_manifest['patches']:
        old_patch = read(old['patch'])
        source = old_patch['source']
        data = read(old_patch['input'])
        positions = np.asarray(data['positions'], dtype=float).copy()
        for edit in old_patch['vertex_edits']:
            positions[edit['index']] = edit['position']
        edits = []
        for i, weights in enumerate(data['weights']):
            if not any(n.startswith('thumb_') and n.endswith('_l') and w > 0
                       for n, w in weights.items()):
                continue
            total = sum(weights.values())
            blend = sum(transfers[n] * (w / total) for n, w in weights.items())
            canonical = np.linalg.solve(blend, np.r_[positions[i], 1.])
            longitudinal = float((inverse_hand @ canonical)[0] * 100.)
            result = partition(weights, longitudinal, float(thumb_root))
            if not result:
                continue
            target, transferred, retention = result
            edits.append(dict(index=i, original_position=positions[i].tolist(),
                original_weights=weights, weights=target,
                canonical_hand_longitudinal_cm=longitudinal,
                thumb_weight_transferred_to_hand=transferred,
                thumb_retention=retention))
        evidence.append(dict(source=source, selected=len(edits),
            proximal_extent_cm=min((x['canonical_hand_longitudinal_cm'] for x in edits), default=None),
            max_removed_thumb_weight=max((x['thumb_weight_transferred_to_hand'] for x in edits), default=0.)))
        if not edits:
            continue
        name = source.rsplit('/', 1)[-1].split('.')[0]
        path = OUT / (name + '.wrist_weight_patch.json')
        expected = installed[source]['after_sha256']
        patch = dict(schema='m16_proximal_thumb_weight_partition_v1',
            source=source, source_sha256=expected, input=old_patch['input'],
            input_sha256=digest(old_patch['input']), vertex_count=len(positions),
            arm_ids=data.get('arm_ids'),
            vertex_index_space=old_patch['vertex_index_space'],
            vertex_edits=edits, reference_bones_changed=False,
            positions_changed=False, topology_uv_normals_materials_changed=False)
        write(path, patch)
        entries.append(dict(source=source, patch=str(path), patch_sha256=digest(path),
                            edited_vertex_count=len(edits)))
    # Provide the same source change for future editable production; do not
    # rewrite the previous, already installed, author's data or Blend file.
    editable = read(PREVIOUS / 'Authored/M16_BareArmsV7_CommonWrist_Editable.json')
    for i, (p, weights) in enumerate(zip(editable['canonical_positions'], editable['weights'])):
        longitudinal = float((inverse_hand @ np.r_[p, 1.])[0] * 100.)
        result = partition(weights, longitudinal, float(thumb_root))
        if result:
            editable['weights'][i] = result[0]
    editable['contract'] += '; proximal thumb influence repartitioned to hand_l without surface/reference changes'
    editable_path = OUT / 'M16_BareArmsV7_WristWeightPartition_Editable.json'
    write(editable_path, editable)
    write(OUT / 'authoring.json', dict(schema='m16_wrist_thumb_weight_partition_authoring_v1',
        source_manifest=str(PREVIOUS / 'Authored/authoring.json'),
        source_manifest_sha256=digest(PREVIOUS / 'Authored/authoring.json'),
        canonical=str(CANONICAL), canonical_sha256=digest(CANONICAL),
        rule=dict(wrist_boundary_cm=-.5, unchanged_at_thumb_root_cm=float(thumb_root),
                  transition='smoothstep by canonical hand longitudinal coordinate',
                  transferred_to='hand_l', no_vertex_position_edits=True),
        anatomy_source_findings=dict(
            hand_and_forearm_helper_guard_locals_equal_reference=True,
            thumb_root_guard_rotation_from_reference_degrees=128.352362578,
            source_issue='thumb_01 weight extends behind hand_l wrist joint; fist opposition pulls wrist heel',
            no_uniform_wrist_scale=True, no_smoothing=True),
        patches=entries, scoped_sources=evidence,
        editable_source=str(editable_path), editable_source_sha256=digest(editable_path),
        install_entry=str(HERE / 'install_wrist_weight_partition.py'),
        native_reference_preserved=True, geometry_preserved=True,
        shared_skeleton_preserved=True, existing_animation_assets_preserved=True,
        ue_imported=False, runtime_tested=False, rendered=False))
    print('WRIST_WEIGHT_PARTITION_AUTHORED', len(entries), sum(e['edited_vertex_count'] for e in entries))


if __name__ == '__main__':
    main()
