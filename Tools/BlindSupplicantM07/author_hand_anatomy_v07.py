"""Produce original-M07 human hand guides and restricted skin fields.

This is source geometry authoring, without changing visible vertices or UVs.
Distal branches are found by connected components of the welded mesh, and
their roots are followed back through the real surface graph. A short fork
beside each little finger is kept and driven by that finger's single chain.
The thumb has CMC, MCP and IP articulation; its four generic chain points
must not be described as an extra PIP/DIP joint.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix, csr_matrix
from scipy.sparse.csgraph import connected_components, dijkstra


ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
FINGERS = ('thumb', 'index', 'middle', 'ring', 'pinky')


def unit(v):
    v = np.asarray(v, dtype=np.float64)
    return v / max(float(np.linalg.norm(v)), 1e-12)


def smoothstep(v):
    v = np.clip(v, 0.0, 1.0)
    return v * v * (3.0 - 2.0 * v)


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def segment_distance(points, a, b):
    ab = b - a
    t = np.clip((points - a) @ ab / max(ab @ ab, 1e-12), 0., 1.)
    return np.linalg.norm(points - (a + t[:, None] * ab), axis=1)


def build_hand(source, side, sign):
    raw = source['positions'].astype(np.float64)
    source_ids = np.flatnonzero((raw[:, 0] * sign > .575) & (raw[:, 1] > .345)
                                & (raw[:, 1] < .515) & (raw[:, 2] > -.145))
    integer, inverse = np.unique(np.rint(raw[source_ids] * 1e6).astype(np.int32),
                                 axis=0, return_inverse=True)
    vertices = integer.astype(np.float64) * 1e-6
    source_to_local = np.full(len(raw), -1, dtype=np.int32)
    source_to_local[source_ids] = inverse
    triangles = source['indices']
    inside = np.all(source_to_local[triangles] >= 0, axis=1)
    faces = source_to_local[triangles[inside]]
    edges = np.concatenate((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]))
    edges.sort(axis=1)
    edges = np.unique(edges, axis=0)
    edges = edges[edges[:, 0] != edges[:, 1]]
    lengths = np.linalg.norm(vertices[edges[:, 0]] - vertices[edges[:, 1]], axis=1)
    graph = coo_matrix((np.r_[lengths, lengths],
                        (np.r_[edges[:, 0], edges[:, 1]], np.r_[edges[:, 1], edges[:, 0]])),
                       shape=(len(vertices), len(vertices))).tocsr()
    vx = vertices[:, 0] * sign

    def components_at(cut):
        active = vx > cut
        remap = np.full(len(vertices), -1, dtype=np.int32)
        remap[active] = np.arange(active.sum())
        use = np.all(active[edges], axis=1)
        e = remap[edges[use]]
        sparse = coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])),
                             shape=(int(active.sum()), int(active.sum()))).tocsr()
        n, labels = connected_components(sparse, directed=False)
        ids = np.flatnonzero(active)
        components = [ids[labels == i] for i in range(n) if np.count_nonzero(labels == i) >= 35]
        return sorted(components, key=len, reverse=True)

    distal = components_at(.825)
    descriptions = []
    for component in distal:
        cloud = vertices[component]
        descriptions.append({'ids': component, 'center': cloud.mean(axis=0),
                             'tip': float(np.max(cloud[:, 0] * sign))})
    # Five main digit shafts are semantic surface branches. The low little-
    # finger fork has the same lateral lane but a shorter terminal extent.
    thumb = max(descriptions, key=lambda d: d['center'][2])
    remaining = [d for d in descriptions if d is not thumb]
    ordered = sorted(remaining, key=lambda d: d['center'][2], reverse=True)
    index = ordered[0]
    middle = max(remaining, key=lambda d: d['tip'])
    ring = min((d for d in remaining if d is not index and d is not middle),
               key=lambda d: abs(d['center'][2] - (middle['center'][2] - .032)))
    little_candidates = [d for d in remaining if d is not index and d is not middle and d is not ring]
    pinky = max(little_candidates, key=lambda d: d['tip'])
    main = [thumb, index, middle, ring, pinky]
    extras = [d for d in descriptions if all(d is not item for item in main)]
    # Seeding all genuine distal shaft vertices prevents a single nearest-
    # vertex label from leaking from the palm into a neighboring digit.
    all_seed_ids = [d['ids'].copy() for d in main]
    extra_records = []
    for extra in extras:
        owner = int(np.argmin([abs(extra['center'][2] - d['center'][2]) for d in main]))
        all_seed_ids[owner] = np.r_[all_seed_ids[owner], extra['ids']]
        extra_records.append({'driven_by': FINGERS[owner], 'source_center': extra['center'].tolist(),
                              'vertex_count': len(extra['ids']), 'tip_absolute_source_x': extra['tip'],
                              'handling': 'Keep the original secondary surface fork; no extra finger chain'})
    super_nodes = len(vertices) + np.arange(5)
    seeded_edges = []
    for owner, ids in enumerate(all_seed_ids):
        seeded_edges.extend((int(super_nodes[owner]), int(i)) for i in ids)
    se = np.asarray(seeded_edges, dtype=np.int32)
    super_graph = coo_matrix((np.r_[lengths, lengths, np.full(len(se), 1e-10), np.full(len(se), 1e-10)],
                             (np.r_[edges[:, 0], edges[:, 1], se[:, 0], se[:, 1]],
                              np.r_[edges[:, 1], edges[:, 0], se[:, 1], se[:, 0]])),
                            shape=(len(vertices) + 5, len(vertices) + 5)).tocsr()
    distance_fields = dijkstra(super_graph, directed=False, indices=super_nodes)[:, :len(vertices)]
    branch = np.argmin(distance_fields, axis=0).astype(np.int8)
    finite = np.isfinite(distance_fields).any(axis=0)
    # Isolated source slivers have no graph route; attach them to the closest
    # actual shaft center with a large depth penalty, never a quantile lane.
    if not finite.all():
        centers = np.stack([d['center'] for d in main])
        d = (vertices[~finite, None, :] - centers[None, :, :]) ** 2
        branch[~finite] = np.argmin(d[..., 1] + d[..., 2] * 3., axis=1)

    # Recover the fork levels by sweeping mesh connectivity toward the palm.
    # A fork root is the last level where its main shaft joins another shaft.
    representative = [int(d['ids'][len(d['ids']) // 2]) for d in main]
    merged_at = np.zeros(5)
    sweep = []
    for cut in np.arange(.696, .824, .002):
        comps = components_at(float(cut))
        for component in comps:
            labels_here = [i for i, seed in enumerate(representative) if np.any(component == seed)]
            if len(labels_here) > 1:
                merged_at[labels_here] = cut
        sweep.append({'cut_source_abs_x': round(float(cut), 5),
                      'substantial_components': len(comps)})

    # Section width identifies the wrist-to-palm fan transition. Average the
    # left/right stable narrow-wrist evidence rather than use cuff topology
    # density as a center of mass (left metal cuff is much more tessellated).
    profile = []
    for x in np.arange(.596, .684, .004):
        cloud = vertices[np.abs(vx - x) < .003]
        yz = (np.quantile(cloud[:, 1:], .05, axis=0)
              + np.quantile(cloud[:, 1:], .95, axis=0)) * .5
        width = float(np.quantile(cloud[:, 2], .95) - np.quantile(cloud[:, 2], .05))
        profile.append({'x': float(x), 'section_center_yz': yz.tolist(), 'depth_width': width})
    base_width = np.median([v['depth_width'] for v in profile if v['x'] <= .616])
    fan_candidates = [v for v in profile if v['x'] >= .624 and v['depth_width'] > base_width * 1.32]
    fan_x = fan_candidates[0]['x'] if fan_candidates else .652
    wrist_x = float(np.clip(fan_x - .012, .625, .647))
    wrist_cloud = vertices[np.abs(vx - wrist_x) < .007]
    wrist_yz = (np.quantile(wrist_cloud[:, 1:], .08, axis=0)
                + np.quantile(wrist_cloud[:, 1:], .92, axis=0)) * .5
    wrist = np.r_[sign * wrist_x, wrist_yz]

    chains = {}
    meta_heads = {}
    axes = {}
    chain_evidence = {}
    radii = {}
    for i, finger in enumerate(FINGERS):
        shaft = vertices[main[i]['ids']]
        # Main centerline excludes the preserved secondary little-finger fork.
        anchor = main[i]['center']
        cloud = vertices[branch == i]
        upper_select = np.ones(len(cloud), dtype=bool)
        if finger == 'pinky':
            upper_select = cloud[:, 1] > anchor[1] - .012
        if finger == 'thumb':
            upper_select = cloud[:, 1] < anchor[1] + .030
        shaft_cloud = cloud[upper_select]
        sx = shaft_cloud[:, 0] * sign
        tip_x = float(np.quantile(shaft[:, 0] * sign, .996))
        tip_cloud = shaft[(shaft[:, 0] * sign) > tip_x - .004]
        tip = np.r_[sign * tip_x, np.median(tip_cloud[:, 1:], axis=0)]
        separation = float(merged_at[i])
        if finger == 'thumb':
            # UE's three thumb deform bones represent metacarpal and two
            # phalanges. CMC is inside the real thumb-side palm, not at the
            # finger-fan knuckle line used by the four other digits.
            base_x = max(wrist_x + .050, separation - .036)
            targets = [base_x, separation + .018, separation + (tip_x - separation) * .66, tip_x]
            names = ['CMC', 'MCP', 'IP', 'tip']
        else:
            base_x = separation - .010
            targets = [base_x, base_x + (tip_x - base_x) * .49,
                       base_x + (tip_x - base_x) * .77, tip_x]
            names = ['MCP', 'PIP', 'DIP', 'tip']
        centers = []
        widths = []
        chosen_x = []
        for j, x in enumerate(targets):
            # Radius minima near expected anatomical joints select the real
            # neck of the digit surface; the anatomical ratio only supplies
            # a search interval on surfaces without modeled knuckle creases.
            if j in (1, 2):
                candidates = []
                half = min(.010, (tip_x - base_x) * .06)
                for test_x in np.linspace(x - half, x + half, 15):
                    c = shaft_cloud[np.abs(sx - test_x) < .004]
                    if len(c) < 8:
                        continue
                    width_yz = np.quantile(c[:, 1:], .90, axis=0) - np.quantile(c[:, 1:], .10, axis=0)
                    radius = float(np.linalg.norm(width_yz)) * .5
                    # Keep placement close to the human segment proportions
                    # when smooth organic taper has no discrete neck.
                    score = radius + ((test_x - x) / max(half, 1e-8)) ** 2 * .004
                    candidates.append((score, test_x))
                if candidates:
                    x = min(candidates)[1]
            c = shaft_cloud[np.abs(sx - x) < .006]
            if len(c) < 10:
                c = shaft_cloud[np.argsort(abs(sx - x))[:40]]
            # Exclude palm points outside the fitted digit's measured depth.
            near = np.abs(c[:, 2] - anchor[2]) < (.020 if finger != 'thumb' else .029)
            if np.count_nonzero(near) >= 8:
                c = c[near]
            low, high = np.quantile(c[:, 1:], [.08, .92], axis=0)
            center = np.r_[sign * x, (low + high) * .5]
            if j == 3:
                center = tip
            centers.append(center)
            widths.append(float(np.linalg.norm(high - low)) * .5)
            chosen_x.append(float(x))
        chain = np.asarray(centers)
        chains[finger] = chain
        radii[finger] = widths
        meta = wrist * .76 + chain[0] * .24
        # Place each metacarpal base at its own actual radial palm sector.
        meta[2] = wrist[2] * .72 + chain[0, 2] * .28
        meta_heads[finger] = meta
        flex = []
        bend = []
        for a, b in zip(chain[:-1], chain[1:]):
            along = unit(b - a)
            flex_direction = np.array([0., -1., 0.])
            if finger == 'thumb':
                flex_direction = unit([0., -.65, -.75])
            axis = unit(np.cross(along, flex_direction))
            flex.append(axis.tolist())
            bend.append(unit(np.cross(axis, along)).tolist())
        axes[finger] = {'flexion_axes_source': flex, 'flexion_directions_source': bend,
                        'metacarpal_axis_source': unit(chain[0] - meta).tolist(),
                        'thumb_opposition_axis_source': unit(chain[0] - wrist).tolist() if finger == 'thumb' else None}
        chain_evidence[finger] = {'joint_names': names, 'graph_fork_source_abs_x': separation,
                                 'joint_source_abs_x': chosen_x, 'section_radii_source': widths,
                                 'distal_main_source_vertex_count': len(main[i]['ids']),
                                 'distal_main_center_source': anchor.tolist(),
                                 'centerline_method': 'Measured digit branch sections, source thickness minima near human articulation intervals'}

    # Fields use actual semantic branches, never neighboring fingers' nearest
    # bones. Palm fan may blend adjacent metacarpals; phalanges remain exclusive.
    bone_names = [f'lowerarm_{side}', f'hand_{side}']
    bone_names += [f'{f}_metacarpal_{side}' for f in FINGERS]
    bone_names += [f'{f}_{j:02d}_{side}' for f in FINGERS for j in (1, 2, 3)]
    lookup = {n: i for i, n in enumerate(bone_names)}
    weights = np.zeros((len(vertices), len(bone_names)), dtype=np.float64)
    branch_start = np.asarray([chains[f][0, 0] * sign for f in FINGERS])
    # Only the wrist taper connects this separately produced field to the
    # body's arm solver; beyond that, hand anatomy owns its own skin field.
    coverage = smoothstep((vx - (wrist_x - .048)) / .052)
    palm_distances = np.stack([segment_distance(vertices, meta_heads[f], chains[f][0])
                              for f in FINGERS], axis=1)
    palm_meta = 1. / np.maximum(palm_distances, .009) ** 3
    palm_meta /= palm_meta.sum(axis=1, keepdims=True)
    mid_knuckle = float(np.median(branch_start[1:]))
    palm_amount = smoothstep((vx - wrist_x) / max(mid_knuckle - wrist_x, .045)) * .88
    weights[:, lookup[f'hand_{side}']] = 1. - palm_amount
    for i, finger in enumerate(FINGERS):
        weights[:, lookup[f'{finger}_metacarpal_{side}']] = palm_amount * palm_meta[:, i]
    # The local wrist field includes a physically smooth hand/forearm roll,
    # while the parent merge alpha avoids overwriting distal forearm weights.
    wrist_hand = smoothstep((vx - (wrist_x - .020)) / .035)
    weights *= wrist_hand[:, None]
    weights[:, lookup[f'lowerarm_{side}']] = 1. - wrist_hand

    for i, finger in enumerate(FINGERS):
        selected = branch == i
        ids = np.flatnonzero(selected)
        x = vx[ids]
        c = chains[finger][:, 0] * sign
        # A little-finger fork shares this longitudinal curve. Its surface
        # is preserved; it cannot create an independently rotating extra hand.
        start_width = min(.012, (c[1] - c[0]) * .20)
        p_width = min(.010, (c[1] - c[0]) * .16)
        d_width = min(.008, (c[2] - c[1]) * .19)
        a = smoothstep((x - (c[0] - start_width)) / (2 * start_width))
        p = smoothstep((x - (c[1] - p_width)) / (2 * p_width))
        d = smoothstep((x - (c[2] - d_width)) / (2 * d_width))
        field = np.zeros((len(ids), len(bone_names)))
        field[:, lookup[f'{finger}_metacarpal_{side}']] = 1. - a
        field[:, lookup[f'{finger}_01_{side}']] = a * (1. - p)
        field[:, lookup[f'{finger}_02_{side}']] = a * p * (1. - d)
        field[:, lookup[f'{finger}_03_{side}']] = a * p * d
        takeover = smoothstep((x - (c[0] - .016)) / .024)
        # This is hand-to-digit blending at the real MCP/CMC, with no
        # adjacency smoothing across the gaps or web boundaries.
        weights[ids] = weights[ids] * (1. - takeover[:, None]) + field * takeover[:, None]

    weights /= weights.sum(axis=1, keepdims=True)
    parents = {f'hand_{side}': f'lowerarm_{side}'}
    joints = {}
    for finger in FINGERS:
        meta = f'{finger}_metacarpal_{side}'
        parents[meta] = f'hand_{side}'
        joints[meta] = {'head_source': meta_heads[finger].tolist(), 'tail_source': chains[finger][0].tolist()}
        for j in (1, 2, 3):
            name = f'{finger}_{j:02d}_{side}'
            parents[name] = meta if j == 1 else f'{finger}_{j-1:02d}_{side}'
            joints[name] = {'head_source': chains[finger][j-1].tolist(),
                            'tail_source': chains[finger][j].tolist(),
                            'flexion_axis_source': axes[finger]['flexion_axes_source'][j-1],
                            'frame_axes_source_columns': [axes[finger]['flexion_axes_source'][j-1],
                                                          unit(chains[finger][j]-chains[finger][j-1]).tolist(),
                                                          axes[finger]['flexion_directions_source'][j-1]],
                            'positive_local_x_rotation': 'Curl toward palm'}
    along = unit(chains['middle'][0] - wrist)
    across = unit(chains['index'][0] - chains['pinky'][0])
    normal = unit(np.cross(along, across))
    record = {'side': side, 'wrist_source': wrist.tolist(),
              'finger_chains_source': {f: chains[f].tolist() for f in FINGERS},
              'finger_chain_joint_names': {f: chain_evidence[f]['joint_names'] for f in FINGERS},
              'metacarpal_heads_source': {f: meta_heads[f].tolist() for f in FINGERS},
              'axes_source': axes, 'bone_parent': parents, 'bones_source': joints,
              'hand_longitudinal_axis_source': along.tolist(), 'hand_fan_axis_source': across.tolist(),
              'hand_normal_source': normal.tolist(), 'thumb_anatomy': 'Three existing thumb deform segments map CMC-MCP-IP-tip; thumb_metacarpal is a proximal support helper, not an extra phalanx',
              'source_vertex_count': len(source_ids), 'welded_vertex_count': len(vertices),
              'source_distal_components': [{'center_source': d['center'].tolist(),
                                            'tip_absolute_source_x': d['tip'],
                                            'vertex_count': len(d['ids'])} for d in descriptions],
              'secondary_forks': extra_records, 'digit_evidence': chain_evidence,
              'wrist_fan_source_abs_x': fan_x, 'wrist_cross_sections_source': profile,
              'mesh_branch_sweep': sweep,
              'field_boundary_source_abs_x': [wrist_x - .048, wrist_x + .004]}
    return record, source_ids, bone_names, weights[inverse], coverage[inverse], branch[inverse]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    output = args.root / 'RecoveryOriginalV07/hands'
    output.mkdir(parents=True, exist_ok=True)
    source = np.load(args.root / 'Authoring/source_mesh.npz')
    records = {}
    ids_all, weights_all, alpha_all, branch_all, side_all = [], [], [], [], []
    side_outputs = []
    names = []
    for side, sign in (('l', 1), ('r', -1)):
        rec, ids, bones, field, alpha, branch = build_hand(source, side, sign)
        records[side] = rec
        side_outputs.append((side, ids, bones, field, alpha, branch))
        names.extend(bones)
    global_lookup = {n: i for i, n in enumerate(names)}
    for side, ids, bones, field, alpha, branch in side_outputs:
        top = np.argsort(field, axis=1)[:, -8:][:, ::-1]
        indices = np.asarray([global_lookup[n] for n in bones], dtype=np.int16)[top]
        weights = np.take_along_axis(field, top, axis=1)
        weights /= weights.sum(axis=1, keepdims=True)
        indices[weights < 1e-9] = -1
        weights[weights < 1e-9] = 0.
        ids_all.append(ids.astype(np.int32)); weights_all.append((indices, weights.astype(np.float32)))
        alpha_all.append(alpha.astype(np.float32)); branch_all.append(branch)
        side_all.append(np.full(len(ids), 1 if side == 'l' else -1, dtype=np.int8))
    ordering = np.argsort(np.concatenate(ids_all))
    np.savez_compressed(output / 'hand_weights_v07.npz',
                        source_vertex_ids=np.concatenate(ids_all)[ordering],
                        bone_names=np.asarray(names),
                        indices=np.concatenate([w[0] for w in weights_all])[ordering],
                        weights=np.concatenate([w[1] for w in weights_all])[ordering],
                        blend_alpha=np.concatenate(alpha_all)[ordering],
                        finger_semantic=np.concatenate(branch_all)[ordering],
                        side_code=np.concatenate(side_all)[ordering])
    anatomy = {'revision': 'OriginalV07', 'source_coordinate_system': 'Original GLB x lateral, y up, z depth; scale and ground remain parent rig responsibility',
               'source_mesh': str(args.root / 'Authoring/source_mesh.npz'),
               'visible_geometry_changed': False, 'uv_changed': False,
               'method': 'Welded-surface graph distal branches, actual fork sweep, measured sections and restricted anatomical skin field',
               'sides': records, 'wrist_source': {s: records[s]['wrist_source'] for s in records},
               'finger_chains_source': {s: records[s]['finger_chains_source'] for s in records},
               'metacarpal_heads_source': {s: records[s]['metacarpal_heads_source'] for s in records},
               'untested': True, 'rendered': False}
    save_json(output / 'hand_anatomy_v07.json', anatomy)
    manifest = {'revision': 'OriginalV07', 'source_mesh': anatomy['source_mesh'],
                'anatomy_path': str(output / 'hand_anatomy_v07.json'),
                'weight_path': str(output / 'hand_weights_v07.npz'),
                'source_vertex_count': int(sum(len(v) for v in ids_all)),
                'bone_names': names, 'max_influences': 8,
                'merge': 'For each source_vertex_id, replace = blend_alpha * this sparse field + (1 - blend_alpha) * parent body field, then sort strongest 8 and normalize',
                'index_space': 'indices index this NPZ bone_names; -1 represents unused influences',
                'finger_semantic': {str(i): f for i, f in enumerate(FINGERS)},
                'region': 'Actual original distal forearm/wrist/palm/fingers only; no visible or UV modification',
                'smoothing': 'No cross-finger adjacency diffusion; skin along each real finger branch and permit metacarpal palm fan blending',
                'thumb_semantics': 'CMC-MCP-IP-tip; proximal thumb_metacarpal support helper may be added without inventing a third thumb phalanx',
                'required_added_bones': ['thumb_metacarpal_l', 'thumb_metacarpal_r'],
                'runtime_tested': False, 'previewed': False, 'user_accepted': False}
    save_json(output / 'hand_weight_manifest.json', manifest)
    gestures = {
        'Idle': {'thumb': [8, 12, 8], 'index': [7, 12, 8], 'middle': [10, 15, 10],
                 'ring': [12, 18, 12], 'pinky': [14, 20, 14]},
        'Locomotion': {'thumb': [8, 12, 8], 'index': [8, 13, 8], 'middle': [11, 16, 10],
                      'ring': [13, 19, 12], 'pinky': [15, 21, 14]},
        'Attack': {'thumb': [14, 18, 10], 'index': [18, 25, 12], 'middle': [20, 27, 14],
                   'ring': [22, 29, 15], 'pinky': [24, 30, 16]},
        'HitOpen': {'thumb': [4, 7, 4], 'index': [3, 6, 3], 'middle': [4, 7, 4],
                    'ring': [5, 8, 4], 'pinky': [6, 9, 5]},
        'DeathRelax': {'thumb': [8, 12, 8], 'index': [10, 16, 9], 'middle': [12, 18, 11],
                       'ring': [14, 20, 12], 'pinky': [16, 22, 14]},
    }
    save_json(output / 'hand_action_guides_v07.json', {
        'revision': 'OriginalV07', 'angles_in_degrees': True,
        'rotation': 'Use the source-space flexion axis on each actual bone frame; if frame_axes_source_columns is used for Blender bones, positive local X curls toward the palm',
        'finger_bone_order': ['01', '02', '03'],
        'thumb_bone_order_semantics': ['CMC to MCP metacarpal', 'MCP to IP proximal phalanx', 'IP to tip distal phalanx'],
        'metacarpal_helpers': 'Four finger metacarpals carry palm fan skin. Thumb helper stabilizes proximal CMC support; leave helpers near neutral rather than apply a duplicate full curl',
        'recommended_curl_degrees': gestures,
        'locomotion_variation': 'At most 2 degrees of phased curl around Locomotion; avoid a rigid identical fist on both hands',
        'attack_usage': 'Interpolate Idle to Attack during existing windup and return to Idle during recovery; retain existing attack contact timings',
        'hit_usage': 'Interpolate toward HitOpen at impact, then return to Idle during existing recovery',
        'thumb_opposition': 'Existing thumb 01 CMC motion owns opposition. Do not label a third thumb phalanx or animate both thumb support helper and thumb 01 with the same full rotation',
        'untested': True, 'rendered': False,
    })
    print(json.dumps({'anatomy': str(output / 'hand_anatomy_v07.json'),
                      'weights': str(output / 'hand_weights_v07.npz'),
                      'source_vertices': manifest['source_vertex_count'],
                      'bones': len(names), 'runtime_tested': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
