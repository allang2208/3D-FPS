"""Shared offline data for the M4 bare-skin V9 sample.

Geometry source = the V8 read-back snapshot of the live viewmodel (asset hash checked);
labels and the reference skeleton come from the V8 master, which was authored from this mesh.
Region labels: 0 upper arm, 1 forearm, 2 hand (master triangle_materials).
"""
import json, hashlib, collections
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree

P = Path('D:/FPS3D/FPSGAME'); R = P / 'SourceAssets/BareSkinV9M4_20261017'
VIEWMODEL = '/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416.SK_M4_FoldingSights_HK416'
SNAPSHOT = P / 'SourceAssets/BareHandAudit20261016/Final/56a5bcfd1c23.json'
MASTER = P / 'SourceAssets/ModularOutfit20260925/BarePalmV7/M4_original.json'
ASSET = P / 'Content/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416.uasset'


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


class M4:
    def __init__(self, check_asset=False):
        s = json.loads(SNAPSHOT.read_text()); m = json.loads(MASTER.read_text())
        if check_asset and sha(ASSET) != s['source_sha256']:
            raise RuntimeError('Viewmodel changed since the V8 snapshot; re-snapshot first')
        self.snap = s
        self.X = np.array(s['positions']); self.T = np.array(s['triangles']); self.N = np.array(s['normals'])
        self.UV = np.array(s['uv']); self.section = np.array(s['triangle_materials'])
        self.W = s['weights']; self.vertex_ids = s['vertex_ids']; self.triangle_ids = s['triangle_ids']
        self.bones = {k: dict(position=np.array(v['position']), axes=np.array(v['axes']) / 100.0, parent=v['parent'], index=v['index'])
                      for k, v in m['bones'].items()}
        mx = np.array(m['positions']); mt = np.array(m['triangles'])
        tree = cKDTree(mx[mt].mean(axis=1)); d, i = tree.query(self.X[self.T].mean(axis=1))
        if d.max() > .05: raise RuntimeError('Snapshot triangles do not match the master (%.3f cm)' % d.max())
        self.region = np.array(m['triangle_materials'])[i]
        # Weld coincident vertices (UV / section splits) for topology-aware work.
        key = {}; self.weld = np.zeros(len(self.X), int)
        for v, p in enumerate(np.round(self.X, 4)):
            self.weld[v] = key.setdefault(tuple(p), len(key))
        self.nw = len(key)
        self.dominant = [max(w, key=w.get) if w else '' for w in self.W]

    def side(self, v): return 'l' if self.X[v][0] < 0 else 'r'

    def joint(self, name): return self.bones[name]['position']

    def welded_adjacency(self):
        nb = [set() for _ in range(self.nw)]
        for t in self.weld[self.T]:
            for a in range(3):
                for b in range(3):
                    if a != b: nb[t[a]].add(t[b])
        return nb

    def vertex_region(self):
        reg = np.full(len(self.X), -1)
        for ti, t in enumerate(self.T):
            for v in t: reg[v] = max(reg[v], self.region[ti])
        return reg

    def old_masks(self, path=P / 'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/WristContourV4/T_M4OriginalShape_SkinSurface.png'):
        """Per-triangle mean of the accepted atlas masks at the old UV0: R nail, B crease, A palmar skin (hand section only)."""
        from PIL import Image
        img = np.asarray(Image.open(path).convert('RGBA'), dtype=np.float32) / 255
        h, w = img.shape[:2]; uv = self.UV.mean(axis=1)
        x = np.clip((uv[:, 0] * w).astype(int), 0, w - 1); y = np.clip((uv[:, 1] * h).astype(int), 0, h - 1)
        out = img[y, x]; out[self.region != 2] = 0
        return out

    def smooth_normals(self, X=None):
        X = self.X if X is None else X
        fn = np.cross(X[self.T[:, 1]] - X[self.T[:, 0]], X[self.T[:, 2]] - X[self.T[:, 0]])
        ref = np.einsum('ij,ij->', fn, self.N.mean(axis=1)); fn *= np.sign(ref)
        acc = np.zeros((self.nw, 3)); wt = self.weld[self.T]
        for k in range(3): np.add.at(acc, wt[:, k], fn)
        acc /= np.maximum(np.linalg.norm(acc, axis=1, keepdims=True), 1e-12)
        return acc[self.weld]

