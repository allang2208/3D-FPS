"""Pack everything the UE install needs into Work/install_payload.json (plain lists; UE Python has no numpy)."""
import json
import numpy as np
from m4data import M4, R, sha, ASSET

m = M4(); wv = m.weld; W = R / 'Work'
P = np.load(W / 'geometry.npz')['welded']; X = P[wv]
N = np.load(W / 'normals.npy'); UV = np.load(W / 'uv_new.npy')
changed_w = {int(k): v for k, v in json.loads((W / 'weights.json').read_text())['changed'].items()}
weights = {int(m.vertex_ids[v]): changed_w[wv[v]] for v in range(len(m.X)) if wv[v] in changed_w}
shapes = np.load(W / 'correctives.npz')


def geo_normals(Pw):
    tw = wv[m.T]; a, b, c = Pw[tw[:, 0]], Pw[tw[:, 1]], Pw[tw[:, 2]]
    fn = np.cross(b - a, c - a); fn *= np.sign(np.einsum('ij,ij->', fn, m.N.mean(axis=1)))
    acc = np.zeros_like(Pw)
    for k in range(3): np.add.at(acc, tw[:, k], fn)
    return acc / np.maximum(np.linalg.norm(acc, axis=1, keepdims=True), 1e-12)


def rotate(v, a, b):
    axis = np.cross(a, b); s = np.linalg.norm(axis, axis=-1); c = np.einsum('...i,...i->...', a, b)
    k = axis / np.maximum(s, 1e-12)[..., None]
    return v * c[..., None] + np.cross(k, v) * s[..., None] + k * np.einsum('...i,...i->...', k, v)[..., None] * (1 - c)[..., None]


VN = np.zeros((len(m.X), 3))
for c in range(3): VN[m.T[:, c]] = N[:, c]                 # corner normals are per vertex by construction
G0 = geo_normals(P); morphs = {}
for name in shapes.files:
    d = shapes[name]; moved = np.linalg.norm(d, axis=1) > .012
    if not moved.any(): continue
    G1 = geo_normals(P + d)
    rows = []
    for v in range(len(m.X)):
        w = wv[v]
        if not moved[w]: continue
        n = rotate(VN[v], G0[w], G1[w]); n /= np.linalg.norm(n)
        rows.append([int(m.vertex_ids[v]), *map(float, X[v] + d[w]), *map(float, n)])
    morphs[name] = rows
payload = dict(asset_sha256=m.snap['source_sha256'], current_sha256=sha(ASSET), mesh='/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416.SK_M4_FoldingSights_HK416',
               vertex_ids=[int(v) for v in m.vertex_ids], positions=X.round(6).tolist(), old_positions=m.X.round(6).tolist(),
               vertex_normals=VN.round(6).tolist(), triangle_ids=[int(t) for t in m.triangle_ids], uv0=UV.round(7).tolist(),
               weights={str(k): v for k, v in weights.items()}, morphs=morphs, skin_slots=[6, 7])
(W / 'install_payload.json').write_text(json.dumps(payload))
print('PAYLOAD verts', len(X), 'weights', len(weights), 'morphs', {k: len(v) for k, v in morphs.items()})
