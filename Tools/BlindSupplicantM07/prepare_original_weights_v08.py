"""Author coherent weights on the original surface, with anatomical chains.

No donor mesh, animation sampling, rendering or game testing is used here.
UV-seam duplicates receive the same weight field. Body/gill attachment copies
share that field, so splitting cannot introduce different seam transforms.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix, diags
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OUT = ROOT/'RecoveryOriginalV08'


def segment_distance(p, a, b):
    ab = b-a
    t = np.clip((p-a)@ab / max(float(ab@ab), 1.e-10), 0, 1)
    return np.linalg.norm(p-a-t[:, None]*ab, axis=1)


def solve(region_path, rig_path):
    source = np.load(ROOT/'Authoring/source_mesh.npz')
    raw = source['positions'].astype(np.float64)
    faces = source['indices'].reshape(-1, 3)
    labels = np.load(region_path)['face_labels'].astype(np.int8)
    guides = json.loads(Path(rig_path).read_text(encoding='utf-8'))
    heads = {n: np.asarray(p) for n, p in guides['bone_heads_cm'].items()}
    tails = {n: np.asarray(p) for n, p in guides['bone_tails_cm'].items()}
    names = list(heads)
    index = {n: i for i, n in enumerate(names)}
    scale = 310 / (raw[:, 1].max()-raw[:, 1].min())
    p = np.c_[raw[:, 0], -raw[:, 2], raw[:, 1]-raw[:, 1].min()]*scale
    _, first, inverse = np.unique(np.rint(raw/1.e-6).astype(np.int32),
                                  axis=0, return_index=True, return_inverse=True)
    wp = p[first]
    tf = inverse[faces]
    edges = np.concatenate((tf[:, [0, 1]], tf[:, [1, 2]], tf[:, [2, 0]]))
    edges.sort(axis=1)
    edges = np.unique(edges, axis=0)
    edges = edges[edges[:, 0] != edges[:, 1]]
    edge_lengths = np.maximum(np.linalg.norm(wp[edges[:, 0]]-wp[edges[:, 1]], axis=1), .001)
    memberships = np.zeros((len(wp), 7), dtype=bool)
    for label in range(7):
        memberships[np.unique(tf[labels == label]), label] = True
    body_ids = np.flatnonzero(memberships[:, 0])
    body_p = wp[body_ids]
    W = np.zeros((len(wp), len(names)), dtype=np.float32)
    torso = [n for n in ('pelvis', 'spine_01', 'spine_02', 'spine_03', 'spine_04',
                         'spine_05', 'neck_01', 'neck_02', 'head') if n in heads]
    following = dict(zip(torso[:-1], torso[1:]))
    chains = {'torso': torso}
    for side in ('l', 'r'):
        arm = [n+'_'+side for n in ('clavicle', 'upperarm', 'lowerarm', 'hand')]
        leg = [n+'_'+side for n in ('thigh', 'calf', 'hock', 'foot', 'ball') if n+'_'+side in heads]
        chains['arm_'+side] = arm
        chains['leg_'+side] = leg
        following.update(zip(arm[:-1], arm[1:]))
        following.update(zip(leg[:-1], leg[1:]))
        for finger in ('thumb', 'index', 'middle', 'ring', 'pinky'):
            digit = [f'{finger}_{j:02d}_{side}' for j in (1, 2, 3)]
            chains[f'{finger}_{side}'] = ['hand_'+side, *digit]
            following.update(zip(digit[:-1], digit[1:]))

    def distance(n, pts):
        return segment_distance(pts, heads[n], heads.get(following.get(n), tails[n]))

    # Select the limb family before bones. This removes opposite limbs and
    # unrelated fingers from the candidate set even when surfaces are nearby.
    major = ['torso', 'arm_l', 'arm_r', 'leg_l', 'leg_r']
    scores = []
    for key in major:
        radius = 16 if key == 'torso' else 7 if key.startswith('arm') else 9
        score = np.minimum.reduce([distance(n, body_p) for n in chains[key]])/radius
        if key.endswith('_l'):
            score[body_p[:, 0] < -2] = 1.e6
        if key.endswith('_r'):
            score[body_p[:, 0] > 2] = 1.e6
        scores.append(score)
    family = np.argmin(np.stack(scores, axis=1), axis=1)
    for group, key in enumerate(major):
        selected = np.flatnonzero(family == group)
        if not len(selected):
            continue
        pts = body_p[selected]
        candidates = list(chains[key])
        if key.startswith('arm'):
            side = key[-1]
            wrist = heads['hand_'+side]
            digit_keys = [f'{f}_{side}' for f in ('thumb', 'index', 'middle', 'ring', 'pinky')]
            hand_extent = max(np.linalg.norm(tails[chains[d][-1]]-wrist) for d in digit_keys)+8
            hand_zone = np.linalg.norm(pts-wrist, axis=1) < hand_extent
            digit_scores = np.stack([np.minimum.reduce([distance(n, pts) for n in chains[d][1:]])
                                     for d in digit_keys], axis=1)
            digit_choice = np.argmin(digit_scores, axis=1)
            hand_score = distance('hand_'+side, pts)
            digit_active = hand_zone & (digit_scores.min(axis=1) < hand_score*.92)
        else:
            digit_active = np.zeros(len(pts), dtype=bool)

        def field(local_ids, allowed):
            if not len(local_ids):
                return
            values = np.stack([distance(n, pts[local_ids]) for n in allowed], axis=1)
            weights = 1.0/np.maximum(values, 1.5)**3
            # Shoulder/hip junctions can mix with their own torso attachment.
            weights /= weights.sum(axis=1, keepdims=True)
            W[body_ids[selected[local_ids]][:, None], [index[n] for n in allowed]] = weights

        if key.startswith('arm'):
            candidates = [*torso[-5:-2], *candidates]
        elif key.startswith('leg'):
            candidates = ['pelvis', 'spine_01', *candidates]
        field(np.flatnonzero(~digit_active), candidates)
        if key.startswith('arm'):
            for digit, d in enumerate(digit_keys):
                field(np.flatnonzero(digit_active & (digit_choice == digit)), chains[d])

    # Smooth on the original anatomical surface, not in empty Euclidean space.
    # Edges across left/right limb families never transmit weights.
    local = np.full(len(wp), -1, dtype=np.int32)
    local[body_ids] = np.arange(len(body_ids))
    e = edges[(local[edges[:, 0]] >= 0) & (local[edges[:, 1]] >= 0)]
    ei = local[e]
    fa, fb = family[ei[:, 0]], family[ei[:, 1]]
    allowed = (fa == fb) | (fa == 0) | (fb == 0)
    ei = ei[allowed]
    graph = coo_matrix((np.ones(len(ei)*2),
        (np.r_[ei[:, 0], ei[:, 1]], np.r_[ei[:, 1], ei[:, 0]])),
        shape=(len(body_ids), len(body_ids))).tocsr()
    normalized = diags(1.0/np.maximum(np.asarray(graph.sum(axis=1)).ravel(), 1.0))@graph
    original = W[body_ids].copy()
    smooth = original.copy()
    for _ in range(10):
        smooth = .35*original + .65*(normalized@smooth)
    W[body_ids] = smooth/np.maximum(smooth.sum(axis=1, keepdims=True), 1.e-10)

    attachment_distance = np.zeros((len(wp), 7), dtype=np.float32)
    for panel in range(1, 7):
        panel_ids = np.flatnonzero(memberships[:, panel])
        panel_points = wp[panel_ids]
        chain = [f'gill_{panel:02d}_{j:02d}' for j in (0, 1, 2)]
        a, b = heads[chain[0]], tails[chain[-1]]
        axis = b-a
        t = np.clip((panel_points-a)@axis/max(float(axis@axis), 1.e-8), 0, .99999)*2
        low = np.floor(t).astype(np.int8)
        high = np.minimum(low+1, 2)
        leaf = np.zeros((len(panel_ids), len(names)), dtype=np.float32)
        leaf[np.arange(len(panel_ids)), [index[chain[i]] for i in low]] = 1-(t-low)
        leaf[np.arange(len(panel_ids)), [index[chain[i]] for i in high]] += t-low
        seam = memberships[:, 0] & memberships[:, panel]
        seam_ids = np.flatnonzero(seam)
        local_panel = np.full(len(wp), -1, dtype=np.int32)
        local_panel[panel_ids] = np.arange(len(panel_ids))
        e = edges[(local_panel[edges[:, 0]] >= 0) & (local_panel[edges[:, 1]] >= 0)]
        lengths = np.linalg.norm(wp[e[:, 0]]-wp[e[:, 1]], axis=1)
        ee = local_panel[e]
        pg = coo_matrix((np.r_[lengths, lengths], (np.r_[ee[:, 0], ee[:, 1]],
                           np.r_[ee[:, 1], ee[:, 0]])), shape=(len(panel_ids), len(panel_ids))).tocsr()
        if not len(seam_ids):
            raise RuntimeError('Original panel has no body attachment: '+str(panel))
        dist = dijkstra(pg, directed=False, indices=local_panel[seam_ids], min_only=True)
        attachment_distance[panel_ids, panel] = dist
        nearest = cKDTree(wp[seam_ids]).query(panel_points)[1]
        attached = W[seam_ids[nearest]]
        blend = np.clip(dist/18.0, 0, 1)
        blend = blend*blend*(3-2*blend)
        panel_field = attached*(1-blend[:, None]) + leaf*blend[:, None]
        # One source vertex can belong to several display pieces. Shared
        # body roots are immutably retained, never overwritten by a leaf.
        replace = ~memberships[panel_ids, 0]
        W[panel_ids[replace]] = panel_field[replace]

    # Store an eight-influence normalized field. Runtime quantization stays
    # separate from the source field used for UV/normal-preserving reduction.
    bone_ids = np.argpartition(W, -8, axis=1)[:, -8:]
    bone_weights = np.take_along_axis(W, bone_ids, axis=1)
    order = np.argsort(-bone_weights, axis=1)
    bone_ids = np.take_along_axis(bone_ids, order, axis=1).astype(np.int16)
    bone_weights = np.take_along_axis(bone_weights, order, axis=1)
    bone_weights /= np.maximum(bone_weights.sum(axis=1, keepdims=True), 1.e-10)
    np.savez_compressed(OUT/'original_skin_weights_v08.npz',
        bone_indices=bone_ids[inverse], bone_weights=bone_weights[inverse],
        attachment_distance_cm=attachment_distance[inverse], welded_source_ids=inverse)
    record = {'bone_names': names, 'original_source': str(ROOT/'Original/Meshy_AI_Veilwing_07_1001123357_texture.glb'),
        'source_regions': str(region_path), 'rig_guides': str(rig_path),
        'method': 'Anatomical family and digit restricted surface weights; welded seam equality; anchored diffusion on original body edges; geodesic gill attachment blend',
        'body_geometry_replaced': False, 'weight_budget': 8, 'tested': False}
    (OUT/'original_skin_weights_v08.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print('M07_ORIGINAL_SURFACE_WEIGHTS_AUTHORED', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--regions', required=True)
    parser.add_argument('--rig-guides', required=True)
    args = parser.parse_args()
    solve(Path(args.regions), Path(args.rig_guides))
