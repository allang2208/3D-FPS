"""Repair the original M-07 arm and hand field on its welded body surface.

No positions, faces, UVs, rig joints or prior revisions are changed. The old
hard geodesic argmin digit labels are replaced by soft surface distances.
This is a source authoring operation and targeted skin continuity diagnosis,
not a render, editor import or runtime test.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix, diags
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.spatial import cKDTree


ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
FINGERS = ('thumb', 'index', 'middle', 'ring', 'pinky')


def smoothstep(x):
    x = np.clip(x, 0., 1.)
    return x * x * (3. - 2. * x)


def segment_distance(p, a, b):
    ab = b - a
    t = np.clip((p - a) @ ab / max(float(ab @ ab), 1.e-12), 0., 1.)
    return np.linalg.norm(p - a - t[:, None] * ab, axis=1)


def sparse_field(indices, weights, count):
    field = np.zeros((len(indices), count), dtype=np.float32)
    rows = np.broadcast_to(np.arange(len(indices))[:, None], indices.shape)
    np.add.at(field, (rows, indices), weights)
    return field


def pack(field):
    ids = np.argpartition(field, -8, axis=1)[:, -8:]
    values = np.take_along_axis(field, ids, axis=1)
    order = np.argsort(-values, axis=1, kind='stable')
    ids = np.take_along_axis(ids, order, axis=1).astype(np.int16)
    values = np.take_along_axis(values, order, axis=1)
    values /= np.maximum(values.sum(axis=1, keepdims=True), 1.e-12)
    return ids, values.astype(np.float32)


def quantized(field):
    ids, values = pack(field)
    q = np.rint(values * 255).astype(np.int16)
    q[:, 0] += 255 - q.sum(axis=1)
    return sparse_field(ids, q.astype(np.float32) / 255., field.shape[1])


def edge_stats(field, edges, length):
    delta = np.abs(field[edges[:, 0]] - field[edges[:, 1]]).sum(axis=1)
    short = length < 1.
    return {
        'edges': int(len(edges)), 'edges_shorter_1cm': int(short.sum()),
        'short_edges_weight_l1_above_1': int(np.count_nonzero(short & (delta > 1.))),
        'short_edges_weight_l1_above_0_5': int(np.count_nonzero(short & (delta > .5))),
        'max_weight_l1': float(delta.max(initial=0.)),
        'weight_l1_quantiles': {str(q): float(np.quantile(delta, q)) for q in (.5, .9, .99, .999)},
        'max_l1_on_edges_shorter_1cm': float(delta[short].max(initial=0.)),
        'max_l1_per_cm': float((delta / np.maximum(length, .001)).max(initial=0.)),
    }


def soft_digit_ownership(raw, edges, graph, anatomy, sign, scale):
    """Distances travel through skin, never across the empty finger gaps."""
    vx = raw[:, 0] * sign
    active = vx > .825
    remap = np.full(len(raw), -1, dtype=np.int32)
    remap[active] = np.arange(active.sum())
    use = np.all(active[edges], axis=1)
    ee = remap[edges[use]]
    distal_graph = coo_matrix((np.ones(len(ee)), (ee[:, 0], ee[:, 1])),
                              shape=(int(active.sum()), int(active.sum()))).tocsr()
    n, labels = connected_components(distal_graph, directed=False)
    active_ids = np.flatnonzero(active)
    components = [active_ids[labels == i] for i in range(n) if np.count_nonzero(labels == i) >= 35]
    centers = np.stack([raw[c].mean(axis=0) for c in components])
    targets = np.stack([anatomy['digit_evidence'][f]['distal_main_center_source'] for f in FINGERS])
    nearest = np.argmin(np.linalg.norm(targets[:, None] - centers[None], axis=2), axis=1)
    if len(set(nearest.tolist())) != 5:
        raise RuntimeError('Original distal shaft centers no longer identify five distinct branches')
    seeds = [components[i].copy() for i in nearest]
    extras = []
    for i, component in enumerate(components):
        if i in nearest:
            continue
        owner = int(np.argmin(np.abs(centers[i, 2] - targets[:, 2])))
        seeds[owner] = np.r_[seeds[owner], component]
        extras.append({'driven_by': FINGERS[owner], 'welded_vertices': int(len(component)),
                       'center_source': centers[i].tolist(),
                       'tip_absolute_source_x': float(vx[component].max()),
                       'weight_handling': 'Same connected digit field; not an additional skeleton chain',
                       'geometry_note': 'Source secondary pinky fork is real geometry; geometry owner may remove its surplus tip'})
    distances = np.stack([dijkstra(graph, directed=False, indices=s, min_only=True) for s in seeds], axis=1)
    finite = np.isfinite(distances).any(axis=1)
    # A two centimetre surface-distance temperature gives a continuous web
    # transition without allowing nearby but disconnected fingers to blend.
    minimum = distances[finite].min(axis=1, keepdims=True)
    prob = np.zeros((len(raw), 5), dtype=np.float64)
    prob[finite] = np.exp(-(distances[finite] - minimum) / 2.)
    prob[finite] /= prob[finite].sum(axis=1, keepdims=True)
    unconnected = np.flatnonzero(~finite)
    if len(unconnected):
        # Only source fragments lacking any surface route use a same-side
        # nearest connected surface transfer. Their field remains coherent.
        routed = np.flatnonzero(finite)
        nearest_surface = routed[cKDTree(raw[routed] * scale).query(raw[unconnected] * scale)[1]]
        prob[unconnected] = prob[nearest_surface]
    return prob, {'distal_seed_vertices': {f: int(len(s)) for f, s in zip(FINGERS, seeds)},
                  'geodesic_temperature_cm': 2., 'unrouted_fragment_vertices': int(len(unconnected)),
                  'secondary_forks': extras}


def solve_side(side, sign, ids, raw, points, edges, lengths, base, names, anatomy, guides,
               gill_membership, extent_alpha, scale):
    lookup = {n: i for i, n in enumerate(names)}
    p = points[ids]
    xyz = raw[ids]
    vx = xyz[:, 0] * sign
    remap = np.full(len(raw), -1, dtype=np.int32)
    remap[ids] = np.arange(len(ids))
    ee = remap[edges]
    use = np.all(ee >= 0, axis=1)
    ee, el = ee[use], lengths[use]
    graph = coo_matrix((np.r_[el, el], (np.r_[ee[:, 0], ee[:, 1]], np.r_[ee[:, 1], ee[:, 0]])),
                       shape=(len(ids), len(ids))).tocsr()
    prob, branch_report = soft_digit_ownership(xyz, ee, graph, anatomy, sign, scale)
    field = np.zeros_like(base)
    shoulder = float(guides['joint_guides_source'][f'upperarm_{side}'][0] * sign)
    elbow = float(guides['joint_guides_source'][f'lowerarm_{side}'][0] * sign)
    wrist = float(anatomy['wrist_source'][0] * sign)
    upper = smoothstep((vx - (shoulder - .015)) / .065)
    lower = smoothstep((vx - (elbow - .026)) / .052)
    field[:, lookup[f'clavicle_{side}']] = 1. - upper
    field[:, lookup[f'upperarm_{side}']] = upper * (1. - lower)
    field[:, lookup[f'lowerarm_{side}']] = upper * lower

    hand = np.zeros_like(base)
    chains = {f: np.asarray(anatomy['finger_chains_source'][f]) for f in FINGERS}
    metas = {f: np.asarray(anatomy['metacarpal_heads_source'][f]) for f in FINGERS}
    distances = np.stack([segment_distance(xyz, metas[f], chains[f][0]) for f in FINGERS], axis=1)
    palm_prob = 1. / np.maximum(distances, .009) ** 2
    palm_prob /= palm_prob.sum(axis=1, keepdims=True)
    palm_prob = .6 * palm_prob + .4 * prob
    knuckle = float(np.median([chains[f][0, 0] * sign for f in FINGERS[1:]]))
    palm_amount = smoothstep((vx - wrist) / max(knuckle - wrist, .045)) * .88
    hand[:, lookup[f'hand_{side}']] = 1. - palm_amount
    for i, f in enumerate(FINGERS):
        hand[:, lookup[f'{f}_metacarpal_{side}']] = palm_amount * palm_prob[:, i]
    take = np.zeros(len(ids))
    digits = np.zeros_like(base)
    for i, f in enumerate(FINGERS):
        c = chains[f][:, 0] * sign
        width = [min(.014, (c[1] - c[0]) * .22), min(.012, (c[1] - c[0]) * .18),
                 min(.010, (c[2] - c[1]) * .22)]
        a, b, d = [smoothstep((vx - (joint - w)) / (2. * w))
                   for joint, w in zip(c[:3], width)]
        amount = prob[:, i] * smoothstep((vx - (c[0] - .022)) / .036)
        take += amount
        digits[:, lookup[f'{f}_metacarpal_{side}']] += amount * (1. - a)
        digits[:, lookup[f'{f}_01_{side}']] += amount * a * (1. - b)
        digits[:, lookup[f'{f}_02_{side}']] += amount * a * b * (1. - d)
        digits[:, lookup[f'{f}_03_{side}']] += amount * a * b * d
    hand = hand * (1. - take[:, None]) + digits
    hand_amount = smoothstep((vx - (wrist - .017)) / .033)
    field = field * (1. - hand_amount[:, None]) + hand * hand_amount[:, None]

    # Original shoulder and body/gill seams remain anchors. Fade the arm
    # replacement in rather than introduce a new field boundary there.
    alpha = smoothstep((vx - .16) / .09) * extent_alpha[ids]
    locked = gill_membership[ids]
    if locked.any():
        distance = dijkstra(graph, directed=False, indices=np.flatnonzero(locked), min_only=True)
        alpha *= smoothstep(distance / 4.)
    else:
        distance = np.full(len(ids), np.inf)
    alpha[locked] = 0.
    repaired = base * (1. - alpha[:, None]) + field * alpha[:, None]
    repaired /= np.maximum(repaired.sum(axis=1, keepdims=True), 1.e-12)
    # The previous torso-versus-arm family selector also left sharp shoulder
    # ownership boundaries above the deltoid. Smooth only that proximal body
    # region on connected triangles, keeping the existing gill seams locked.
    conductance = 1. / (el * el + .0625)
    adjacency = coo_matrix((np.r_[conductance, conductance],
                            (np.r_[ee[:, 0], ee[:, 1]], np.r_[ee[:, 1], ee[:, 0]])),
                           shape=(len(ids), len(ids))).tocsr()
    degree = np.asarray(adjacency.sum(axis=1)).ravel()
    averaging = diags(1. / np.maximum(degree, 1.e-12)) @ adjacency
    anchor = repaired.copy()
    diffused = repaired.copy()
    for _ in range(8):
        diffused = .15 * anchor + .85 * (averaging @ diffused)
        diffused[degree == 0.] = anchor[degree == 0.]
    sh, elb, wr = [np.asarray(guides['joint_guides_source'][f'{n}_{side}'])
                   for n in ('upperarm', 'lowerarm', 'hand')]
    radius = np.minimum(segment_distance(xyz, sh, elb), segment_distance(xyz, elb, wr))
    proximal = (smoothstep((vx - .16) / .025) * smoothstep((.30 - vx) / .04)
                * smoothstep((.115 - radius) / .020) * smoothstep(distance / 1.))
    proximal[locked] = 0.
    repaired = repaired * (1. - proximal[:, None]) + diffused * proximal[:, None]
    repaired /= np.maximum(repaired.sum(axis=1, keepdims=True), 1.e-12)
    alpha = 1. - (1. - alpha) * (1. - proximal)
    # Diagnose the field actually written with the eight-influence budget.
    packed_ids, packed_values = pack(repaired)
    repaired = sparse_field(packed_ids, packed_values, len(names))
    count, components = connected_components(graph, directed=False)
    loose = []
    detached_wrist_components = 0
    for component in range(count):
        selected = np.flatnonzero(components == component)
        center_x = float(vx[selected].mean())
        if .50 < center_x < wrist + .02 and vx[selected].max() < .80:
            detached_wrist_components += 1
        if len(selected) > 500:
            continue
        mean = repaired[selected].mean(axis=0)
        top = np.argsort(mean)[-4:][::-1]
        loose.append({'welded_vertices': int(len(selected)), 'bounds_cm': [p[selected].min(axis=0).tolist(),
                     p[selected].max(axis=0).tolist()], 'mean_weights': [[names[n], float(mean[n])] for n in top if mean[n] > .01]})
    return repaired, alpha, ee, el, {
        'side': side, 'welded_vertices': int(len(ids)), 'replacement_full_after_source_abs_x': .25,
        'shoulder_source_abs_x': shoulder, 'elbow_source_abs_x': elbow,
        'wrist_source_abs_x': wrist, 'elbow_blend_width_cm': .052 * scale,
        'wrist_blend_width_cm': .033 * scale, 'locked_body_gill_seam_vertices': int(locked.sum()),
        'proximal_shoulder_surface_diffusion': {'iterations': 8, 'anchor_fraction': .15,
            'neighbor_fraction': .85, 'welded_vertices': int(np.count_nonzero(proximal)),
            'source_abs_x_bounds': [.16, .30], 'existing_body_gill_seams_locked': True,
            'body_seam_neighbor_smoothing_release_cm': 1.},
        'detached_wrist_surface_components_found': detached_wrist_components,
        'cuff_handling': 'Forearm shaft is pure ipsilateral lowerarm between elbow and wrist transitions; wrist metal needs no phalanx influence',
        'small_disconnected_source_components': loose, **branch_report,
        'before_source': edge_stats(base, ee, el), 'after_source': edge_stats(repaired, ee, el),
        'before_display_quantization_255': edge_stats(quantized(base), ee, el),
        'after_display_quantization_255': edge_stats(quantized(repaired), ee, el),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root
    out = root / 'RecoveryHandsV11/weights'
    out.mkdir(parents=True, exist_ok=True)
    source = np.load(root / 'Authoring/source_mesh.npz')
    raw = source['positions'].astype(np.float64)
    faces = source['indices']
    regions = np.load(root / 'RecoveryOriginalV06/regions/source_regions_original_v06.npz')
    original = dict(np.load(root / 'RecoveryOriginalV09/gill_skin_weights_v09.npz'))
    record = json.loads((root / 'RecoveryOriginalV09/gill_skin_weights_v09.json').read_text(encoding='utf-8'))
    guides = json.loads((root / 'RecoveryOriginalV08/rig_motion/original_rig_guides.json').read_text(encoding='utf-8'))
    anatomy = json.loads((root / 'RecoveryOriginalV07/hands/hand_anatomy_v07.json').read_text(encoding='utf-8'))
    names = record['bone_names']
    _, first, welded = np.unique(regions['source_welded_vertex_ids'], return_index=True, return_inverse=True)
    wr = raw[first]
    scale = 310. / (raw[:, 1].max() - raw[:, 1].min())
    points = np.c_[wr[:, 0], -wr[:, 2], wr[:, 1] - raw[:, 1].min()] * scale
    body_faces = welded[faces[regions['face_labels'] == 0]]
    edges = np.concatenate([body_faces[:, [0, 1]], body_faces[:, [1, 2]], body_faces[:, [2, 0]]])
    edges.sort(axis=1)
    edges = np.unique(edges, axis=0)
    edges = edges[edges[:, 0] != edges[:, 1]]
    lengths = np.maximum(np.linalg.norm(points[edges[:, 0]] - points[edges[:, 1]], axis=1), .0001)
    body = np.zeros(len(first), dtype=bool)
    body[np.unique(body_faces)] = True
    gill = np.zeros(len(first), dtype=bool)
    gill[np.unique(welded[faces[regions['face_labels'] != 0]])] = True
    new_indices = original['bone_indices'].copy()
    new_weights = original['bone_weights'].copy()
    modified = np.zeros(len(first), dtype=bool)
    solved_ids, solved_indices, solved_weights = [], [], []
    reports = []
    for side, sign in (('l', 1), ('r', -1)):
        heads = guides['joint_guides_source']
        shoulder, elbow, wrist = [np.asarray(heads[f'{n}_{side}']) for n in ('upperarm', 'lowerarm', 'hand')]
        capsule = np.minimum(segment_distance(wr, shoulder, elbow), segment_distance(wr, elbow, wrist))
        vx = wr[:, 0] * sign
        selected = body & (vx > .16) & (wr[:, 1] > .335) & (wr[:, 1] < .575) & (wr[:, 2] > -.19) & (wr[:, 2] < .08)
        selected &= (capsule < .115) | (vx > .55)
        extent_alpha = smoothstep((.115 - capsule) / .05)
        extent_alpha[vx > .55] = 1.
        ids = np.flatnonzero(selected)
        base = sparse_field(original['bone_indices'][first[ids]], original['bone_weights'][first[ids]], len(names))
        repaired, alpha, _, _, report = solve_side(side, sign, ids, wr, points, edges, lengths, base,
                                                    names, anatomy['sides'][side], guides, gill, extent_alpha, scale)
        packed_indices, packed_weights = pack(repaired)
        changed = alpha > 0.
        modified[ids[changed]] = True
        solved_ids.append(ids[changed]); solved_indices.append(packed_indices[changed]); solved_weights.append(packed_weights[changed])
        report['replacement_vertices_nonzero_alpha'] = int(changed.sum())
        reports.append(report)
        print(f'M07_{side.upper()}_CONTINUOUS_ARM_HAND_FIELD_READY {len(ids)} welded vertices', flush=True)
    repaired_welded_ids = np.concatenate(solved_ids)
    repair_lookup = np.full(len(first), -1, dtype=np.int32)
    repair_lookup[repaired_welded_ids] = np.arange(len(repaired_welded_ids))
    rows = np.flatnonzero(modified[welded])
    new_indices[rows] = np.concatenate(solved_indices)[repair_lookup[welded[rows]]]
    new_weights[rows] = np.concatenate(solved_weights)[repair_lookup[welded[rows]]]
    unchanged = np.ones(len(raw), dtype=bool)
    unchanged[rows] = False
    preservation = (np.array_equal(new_indices[unchanged], original['bone_indices'][unchanged])
                    and np.array_equal(new_weights[unchanged], original['bone_weights'][unchanged]))
    original['bone_indices'] = new_indices
    original['bone_weights'] = new_weights
    original['bone_names'] = np.asarray(names)
    original['repaired_arm_hand_source_vertex_ids'] = rows.astype(np.int32)
    np.savez_compressed(out / 'original_arm_hand_skin_weights_v11.npz', **original)
    # Compare only source rows participating in this authorized hand/arm fix.
    active_first = first[modified]
    probe = repair_lookup[welded[rows]]
    reference_ids = np.concatenate(solved_indices)[probe]
    reference_values = np.concatenate(solved_weights)[probe]
    equivalence = np.array_equal(new_indices[rows], reference_ids) and np.array_equal(new_weights[rows], reference_values)
    # Compare against the diagnosed, actually displayed high mesh using its
    # exact original source IDs and the identical requested hand/arm bounds.
    diagnosed_high = root / 'RecoveryHandsV11/diagnosis/geometry_M07_OriginalBody_High.npz'
    current_high_comparison = None
    if diagnosed_high.exists():
        high = np.load(diagnosed_high)
        p = high['positions_cm']
        arm = (np.abs(p[:, 0]) > 28.) & (p[:, 2] > 215.) & (p[:, 2] < 281.) & (p[:, 1] > -30.) & (p[:, 1] < 45.)
        use = np.all(arm[high['edges']], axis=1)
        ee = high['edges'][use]
        used = np.unique(ee)
        local = np.full(len(p), -1, dtype=np.int32)
        local[used] = np.arange(len(used))
        ee = local[ee]
        el = np.linalg.norm(p[high['edges'][use, 0]] - p[high['edges'][use, 1]], axis=1)
        old = sparse_field(high['bone_indices'][used], high['bone_weights'][used], len(names))
        sids = high['source_vertex_ids'][used]
        new = sparse_field(new_indices[sids], new_weights[sids], len(names))
        current_high_comparison = {'before': edge_stats(old, ee, el),
                                   'after_source': edge_stats(new, ee, el),
                                   'after_display_quantization_255': edge_stats(quantized(new), ee, el)}
    manifest = {
        'revision': 'RecoveryHandsV11', 'bone_names': names, 'bone_count': len(names), 'weight_budget': 8,
        'source_mesh': str(root / 'Authoring/source_mesh.npz'),
        'source_weight_field': str(root / 'RecoveryOriginalV09/gill_skin_weights_v09.npz'),
        'weight_path': str(out / 'original_arm_hand_skin_weights_v11.npz'),
        'method': 'Ipsilateral shoulder-elbow-wrist anatomical field; five soft geodesic distal surface branches; continuous palm and MCP/PIP/DIP or CMC/MCP/IP transitions',
        'visible_geometry_changed': False, 'uv_changed': False, 'bone_names_changed': False,
        'joint_positions_changed': False, 'modified_source_vertices': int(len(rows)),
        'modified_welded_vertices': int(len(active_first)),
        'all_modified_source_uv_copies_receive_identical_fields': bool(equivalence),
        'all_unmodified_source_rows_preserved_byte_for_byte': bool(preservation),
        'original_gill_member_vertices_modified': int(np.count_nonzero(modified & gill)),
        'original_leg_vertices_modified': 0,
        'sides': reports, 'current_high_original_arm_bounds_comparison': current_high_comparison,
        'runtime_tested': False, 'rendered': False, 'user_accepted': False,
        'diagnosis_scope': 'Only requested original hands/arms skin continuity, source fragments and anatomical ownership',
        'display_mapping': 'Blender decimation source_vertex_id is not a reliable weight lookup. Reproject the continuous field from preserved original triangles, then weld coincident display vertices before quantization.',
    }
    (out / 'original_arm_hand_skin_weights_v11.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'weights': manifest['weight_path'], 'modified_source_vertices': len(rows),
                      'source_only': True, 'runtime_tested': False}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
