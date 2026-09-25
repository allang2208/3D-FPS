"""Fit field gloves to the accepted V7 hands and each native weapon binding.

Run in ordinary Python. No animation clips, reference bones or base hands change.
Offsets are centimetres, evaluated once on the shared canonical hand surface.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

PROJECT = Path(__file__).resolve().parents[2]
ROOT = PROJECT / 'SourceAssets/ModularOutfit20260925/FittedFieldGlovesV1'
BARE = PROJECT / 'SourceAssets/ModularOutfit20260925/BarePalmV7'
SOURCES = PROJECT / 'SourceAssets/ModularOutfit20260925/BareArmsFamilyV6/Sources'
OUT = ROOT / 'Authored'
OUT.mkdir(parents=True, exist_ok=True)


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def smooth(a, b, v):
    t = np.clip((v-a)/(b-a), 0, 1)
    return t*t*(3-2*t)


def bind(bone):
    m = np.eye(4)
    m[:3, :3] = np.asarray(bone['axes']).T
    m[:3, 3] = bone['position']
    return m


def vertex_normals(p, t):
    corners = p[t]
    face = -unit(np.cross(corners[:, 1]-corners[:, 0], corners[:, 2]-corners[:, 0]))
    result = np.zeros_like(p)
    for k in range(3):
        a = unit(corners[:, (k+1) % 3]-corners[:, k])
        b = unit(corners[:, (k+2) % 3]-corners[:, k])
        angle = np.arccos(np.clip((a*b).sum(1), -1, 1))
        np.add.at(result, t[:, k], face*angle[:, None])
    return unit(result)


canonical_raw = (BARE/'M4_original.json').read_bytes()
canonical = json.loads(canonical_raw)
anatomy = read(PROJECT/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json')['anatomy']
p = np.asarray(canonical['positions'])
t = np.asarray(canonical['triangles'])
hand_faces = np.flatnonzero(np.asarray(canonical['triangle_materials']) == 2)
hand_t = t[hand_faces]
hand_ids = np.unique(hand_t)
n = vertex_normals(p, t)

# Only the actual boundary of the hidden hand section is the cuff. Preserve its
# exact coordinates and weights, including the wrist loft from the bare master.
edges = Counter(tuple(sorted((int(f[k]), int(f[(k+1) % 3])))) for f in hand_t for k in range(3))
boundary = np.asarray(sorted({v for e, count in edges.items() if count == 1 for v in e}))
ij = np.asarray(list(edges))
lengths = np.linalg.norm(p[ij[:, 0]]-p[ij[:, 1]], axis=1)
graph = coo_matrix((np.r_[lengths, lengths],
                   (np.r_[ij[:, 0], ij[:, 1]], np.r_[ij[:, 1], ij[:, 0]])), shape=(len(p), len(p))).tocsr()
edge_distance = dijkstra(graph, indices=boundary, min_only=True, directed=False)

# Finger-pad orientation comes from its own digit, rather than a single palm
# plane: the accepted fingers are already curled in the reference pose.
dorsal = np.zeros_like(p)
for side, frame in anatomy.items():
    belongs = p[:, 0] < 0 if side == 'l' else p[:, 0] > 0
    digit_dorsal = {d['bone']: np.asarray(d['dorsal']) for d in frame['digits']}
    for vi in np.flatnonzero(belongs):
        w = canonical['weights'][vi]
        total = sum(value for name, value in w.items() if name in digit_dorsal)
        dorsal[vi] = np.asarray(frame['dorsal'])*max(0, 1-total)
        for name, value in w.items():
            if name in digit_dorsal:
                dorsal[vi] += digit_dorsal[name]*value
dorsal = unit(dorsal)
back = smooth(-.15, .65, (n*dorsal).sum(1))
contact_thickness = .015   # 0.15 mm at palm/finger pads; skin below is hidden.
back_thickness = .070      # 0.70 mm on the outer hand, without moving grip bones.
thickness = (contact_thickness + (back_thickness-contact_thickness)*back)
thickness *= smooth(0, .60, edge_distance)
thickness += .025*np.exp(-((edge_distance-.24)/.14)**2)*smooth(0, .16, edge_distance)
offset = np.zeros_like(p)
offset[hand_ids] = n[hand_ids]*thickness[hand_ids, None]
offset[boundary] = 0
new_p = p+offset
new_n = vertex_normals(new_p, t)

# Transport accepted split normals through the small surface deformation.
axis = np.cross(n, new_n)[t]
dot = (n*new_n).sum(1)[t, None]
old_n = np.asarray(canonical['normals'])
glove_normals = unit(old_n + np.cross(axis, old_n) + np.cross(axis, np.cross(axis, old_n))/np.maximum(1+dot, 1e-8))
canonical_native = read(SOURCES/'M4.json')
inverse = {name: np.linalg.inv(bind(b)) for name, b in canonical_native['bones'].items()}
config = read(PROJECT/'Content/ColdSteelData/modular_outfits.json')
manifest = []

for entry in read(BARE/'manifest.json'):
    name = entry['profile']
    raw = Path(entry['authored']).read_bytes()
    bare = json.loads(raw)
    native = read(SOURCES/f'{name}.json')
    profile = config['profiles'][bare['source']]
    rest = np.asarray(bare['canonical_positions'])
    if len(rest) == len(p):
        mapping = np.arange(len(p))
    else:
        side = -1 if rest[:, 0].mean() < 0 else 1
        mapping = np.flatnonzero(p[:, 0]*side > 0)
    # The family author preserves vertex order; positional nearest neighbours
    # are ambiguous at coincident UV/surface seams.
    if len(rest) != len(mapping) or float(np.max(np.linalg.norm(rest-p[mapping], axis=1))) > 1e-7:
        raise RuntimeError('Canonical hand correspondence changed: '+name)
    faces = [i for i, mat in enumerate(bare['triangle_materials']) if mat == 2]
    ids = sorted({v for fi in faces for v in bare['triangles'][fi]})
    remap = {v: i for i, v in enumerate(ids)}
    matrices = {bn: (bind(native['bones'][bn])@inverse[bn])[:3, :3]
                for bn in {bn for vi in ids for bn in bare['weights'][vi]}}
    positions = []
    normals_by_vertex = {}
    for vi in ids:
        matrix = sum(matrices[bn]*weight for bn, weight in bare['weights'][vi].items())
        positions.append((np.asarray(bare['positions'][vi])+matrix@offset[mapping[vi]]).tolist())
        normals_by_vertex[vi] = np.linalg.inv(matrix).T
    canonical_faces = {tuple(face): fi for fi, face in enumerate(canonical['triangles'])}
    normals = []
    canonical_normals = []
    for fi in faces:
        face = bare['triangles'][fi]
        ci = canonical_faces[tuple(int(mapping[vi]) for vi in face)]
        cn = glove_normals[ci]
        normals.append([unit(normals_by_vertex[vi]@cn[k]).tolist() for k, vi in enumerate(face)])
        canonical_normals.append(cn.tolist())
    data = {
        'profile': name, 'source': bare['source'], 'skeleton': bare['skeleton'],
        'binding_source': profile['original_gloved_source'],
        'base_mesh': profile['native_bare_skin'],
        'bare_authored_sha256': hashlib.sha256(raw).hexdigest(),
        'positions': positions, 'weights': [bare['weights'][vi] for vi in ids],
        'triangles': [[remap[vi] for vi in bare['triangles'][fi]] for fi in faces],
        'uv': [bare['uv'][fi] for fi in faces], 'normals': normals,
        'triangle_materials': [0]*len(faces),
        'canonical_positions': [new_p[mapping[vi]].tolist() for vi in ids],
        'canonical_normals': canonical_normals,
        'bare_vertex_ids': ids, 'bare_face_ids': faces,
        'surface_winding': 'ue_native',
        'contract': 'V7 hand section 2; native reference skeleton and exact native weights; fixed cuff boundary; shared existing animations',
    }
    path = OUT/f'{name}.json'
    path.write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
    manifest.append({'profile': name, 'source': bare['source'], 'authored': str(path),
                     'vertices': len(ids), 'triangles': len(faces)})
    print('FITTED_GLOVES_AUTHORED', name, len(ids), len(faces), flush=True)

(ROOT/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
(ROOT/'fit-policy.json').write_text(json.dumps({
    'canonical': str(BARE/'M4_original.json'), 'canonical_sha256': hashlib.sha256(canonical_raw).hexdigest(),
    'contact_thickness_mm': contact_thickness*10, 'dorsal_thickness_mm': back_thickness*10,
    'cuff_blend_mm': 6, 'cuff_lip_extra_mm': .25, 'cuff_boundary': 'Original V7 section 2 boundary, zero displacement and copied weights',
    'new_animations': 0, 'runtime_tested': False,
    'items': ['ue_field_gloves', 'ue_field_gloves_black'], 'third_person': 'Existing Body glove retained',
}, indent=2)+'\n', encoding='utf-8')
