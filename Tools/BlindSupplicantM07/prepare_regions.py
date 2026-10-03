"""Author source-preserving body/gill partitions from the joined Meshy surface.
Semantic guides are editable production inputs, not verified anatomy labels.
"""
import json
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OUT = ROOT / 'Authoring'
src = np.load(OUT / 'source_mesh.npz')
p = src['positions'].astype(np.float64)
faces = src['indices'].reshape(-1, 3)
y0, y1 = float(p[:, 1].min()), float(p[:, 1].max())
height = (p[:, 1] - y0) / (y1 - y0)
scale = 3.1 / (y1 - y0)
guides = {
    'pelvis': [0, -.115, .040],
    'spine_01': [0, -.075, .038],
    'spine_02': [0, .015, .026],
    'spine_03': [0, .125, .002],
    'spine_04': [0, .255, -.040],
    'spine_05': [0, .397, -.080],
    'neck_01': [0, .490, -.035],
    'neck_02': [0, .558, .012],
    'head': [0, .642, .050],
}
for side, sign in [('l', 1), ('r', -1)]:
    guides.update({
        'clavicle_'+side: [sign*.045, .412, -.085],
        'upperarm_'+side: [sign*.190, .423, -.110],
        'lowerarm_'+side: [sign*.570, .377, -.158],
        'hand_'+side: [sign*.846, .355, -.166],
        'thigh_'+side: [sign*.100, -.135, .010],
        'calf_'+side: [sign*.105, -.399, -.085],
        'foot_'+side: [sign*.112, -.651, -.090],
        'ball_'+side: [sign*.143, -.721, .040],
    })

def segment_distance(points, a, b):
    a = np.asarray(a); b = np.asarray(b)
    delta = b-a
    t = np.clip((points-a) @ delta / max(float(delta @ delta), 1e-12), 0, 1)
    return np.linalg.norm(points-(a+t[:, None]*delta), axis=1)

body = np.zeros(len(p), dtype=bool)
capsules = [('pelvis', 'spine_03', .105), ('spine_03', 'spine_05', .120),
            ('spine_05', 'neck_01', .090), ('neck_01', 'head', .120)]
for side in ['l', 'r']:
    capsules.extend([('clavicle_'+side, 'upperarm_'+side, .067),
                     ('upperarm_'+side, 'lowerarm_'+side, .052),
                     ('lowerarm_'+side, 'hand_'+side, .048),
                     ('thigh_'+side, 'calf_'+side, .060),
                     ('calf_'+side, 'foot_'+side, .040),
                     ('foot_'+side, 'ball_'+side, .052)])
for a, b, radius in capsules:
    body |= segment_distance(p, guides[a], guides[b]) < radius
# Source feet, sensory head and exposed distal fingers remain source geometry.
body |= height < .09
body |= (height > .88) & (np.abs(p[:, 0]) < .23)
body |= (np.abs(p[:, 0]) > .62) & (height > .67)
body |= (height < .27) & (np.abs(p[:, 0]) < .155)

# Use the source's joined surface geodesics to partition six gills. UV seam
# duplicates are welded only in this graph, never in the retained visible mesh.
quant = np.rint(p / 1e-6).astype(np.int64)
_, inverse = np.unique(quant, axis=0, return_inverse=True)
count = int(inverse.max()) + 1
centres = np.zeros((count, 3), dtype=np.float64)
np.add.at(centres, inverse, p)
n = np.bincount(inverse)
centres /= n[:, None]
welded_body = np.bincount(inverse, weights=body.astype(float)) / n > .55
wf = inverse[faces]
edges = np.concatenate([wf[:, [0, 1]], wf[:, [1, 2]], wf[:, [2, 0]]])
edges.sort(axis=1)
edges = np.unique(edges, axis=0)
valid = ~(welded_body[edges[:, 0]] | welded_body[edges[:, 1]])
edges = edges[valid]
lengths = np.linalg.norm(centres[edges[:, 0]] - centres[edges[:, 1]], axis=1)
graph = coo_matrix((np.r_[lengths, lengths],
                   (np.r_[edges[:, 0], edges[:, 1]], np.r_[edges[:, 1], edges[:, 0]])),
                  shape=(count, count)).tocsr()
seed_ids = []
seed_records = []
for side, sign in [('l', 1), ('r', -1)]:
    for i, depth in enumerate([-.185, -.125, -.060]):
        lateral = centres[:, 0]*sign
        candidate = np.flatnonzero((lateral >= .19) & (lateral < .37) &
                                    ~welded_body & (centres[:, 1] > .060) & (centres[:, 1] < .280))
        if not len(candidate):
            raise RuntimeError('No source membrane tip in editable guide '+side+str(i))
        target = np.array([sign*.26, .155, depth])
        # Separate the stacked membranes in depth, rather than splitting three
        # neighbouring points on the same long fringe into tiny artificial strips.
        metric = (centres[candidate]-target)*np.array([1.0, 1.0, 3.5])
        seed = int(candidate[np.argmin(np.linalg.norm(metric, axis=1))])
        seed_ids.append(seed)
        seed_records.append({'id': f'{len(seed_ids):02d}', 'side': side,
                             'guide_layer_depth_source': depth,
                             'tip_source': centres[seed].tolist()})
print('Partitioning the joined source surface into six editable gill regions', flush=True)
distance = dijkstra(graph, directed=False, indices=seed_ids)
labels = np.argmin(distance, axis=0).astype(np.int16)+1
unreached = ~np.isfinite(distance.min(axis=0)) & ~welded_body
# Isolated membrane islands from the conservative body guide use nearest seed;
# nothing is discarded from the high-detail original.
if unreached.any():
    labels[unreached] = np.argmin(np.linalg.norm(centres[unreached, None, :]-
                                               centres[seed_ids][None, :, :], axis=2), axis=1)+1
vertex_labels = labels[inverse]
vertex_labels[body] = 0
tri_labels = vertex_labels[faces]
face_labels = np.zeros(len(faces), dtype=np.int16)
for label in range(7):
    votes = (tri_labels == label).sum(axis=1)
    face_labels[votes >= 2] = label
ties = (tri_labels[:, 0] != tri_labels[:, 1]) & (tri_labels[:, 0] != tri_labels[:, 2]) & (tri_labels[:, 1] != tri_labels[:, 2])
face_labels[ties] = tri_labels[ties, 0]
np.savez_compressed(OUT/'source_regions.npz', face_labels=face_labels, vertex_labels=vertex_labels)
record = {'stage': 'source-preserving editable region partition authored',
          'method': 'anatomical volume guides plus membrane-tip geodesic partition; no source face discarded',
          'semantic_partition_user_accepted': False,
          'scale_to_meters': scale, 'ground_source_y': y0,
          'joint_guides_source': guides, 'membrane_tip_guides': seed_records,
          'faces_by_region': {str(i): int((face_labels == i).sum()) for i in range(7)},
          'limitations': 'Region seams and anatomical landmark guides are a first authoring pass; no rendered or runtime inspection performed.',
          'tested': False}
(OUT/'region_authoring.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'saved': str(OUT/'source_regions.npz'), 'faces': record['faces_by_region']}, ensure_ascii=False), flush=True)
