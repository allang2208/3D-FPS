"""Measure the Super90 guide and both receivers' undersides near the loading port (gun frame, metres)."""
import json
from pathlib import Path
import numpy as np
from rig import row2m, inv

O = Path(__file__).parent
D = json.loads((O / 'inputs.json').read_text()); G = json.loads((O / 'geometry.json').read_text())


def to_gun(points_cm, sk):
    root = row2m(sk['ref_world']['WPN_root'])
    return (inv(root) @ np.c_[points_cm, np.ones(len(points_cm))].T).T[:, :3]


g = to_gun(np.array(G['super90_guide']['positions']), D['super90'])
print('super90 guide verts', len(g), 'bbox min', g.min(0).round(4), 'max', g.max(0).round(4))
ys = np.round(g[:, 1], 3)
from collections import Counter
print('guide y histogram (rounded mm):', sorted(Counter(np.round(g[:, 1] * 1000).astype(int)).items())[:40])
top = g[g[:, 1] < g[:, 1].min() + .004]; bot = g[g[:, 1] > g[:, 1].max() - .004]
print('top band n', len(top), 'x', top[:, 0].min().round(4), top[:, 0].max().round(4), 'z', top[:, 2].min().round(4), top[:, 2].max().round(4))
print('bottom band n', len(bot), 'x', bot[:, 0].min().round(4), bot[:, 0].max().round(4), 'z', bot[:, 2].min().round(4), bot[:, 2].max().round(4), 'y', bot[:, 1].mean().round(4))


def tri_mesh(key, sk):
    geo = G[key]; skin = {i for i, s in enumerate(geo['slots']) if any(k in s.lower() for k in ('skin', 'bare', 'manny'))}
    v = to_gun(np.array(geo['positions']), sk); t = np.array(geo['triangles']); m = np.array(geo['materials'])
    dom = np.array(geo['dominant'])
    keep = ~np.isin(m, list(skin)) & np.all(np.isin(dom[t], ['WPN_root', 'WPN_Load', 'WPN_Trigger', 'WPN_bolt']), axis=1)
    return v, t[keep]


def underside(v, t, x, z):
    """Lowest receiver surface (max y, y points down) above the ray from y=0.3 going up (-y)."""
    a, b, c = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
    best = None
    o = np.array([x, .3, z]); d = np.array([0, -1., 0])
    e1, e2 = b - a, c - a; h = np.cross(d, e2); det = np.einsum('ij,ij->i', e1, h)
    ok = np.abs(det) > 1e-12; f = 1 / np.where(ok, det, 1); s = o - a
    u = f * np.einsum('ij,ij->i', s, h); q = np.cross(s, e1); w = f * (q @ d)
    tt = f * np.einsum('ij,ij->i', e2, q)
    hit = ok & (u >= 0) & (w >= 0) & (u + w <= 1) & (tt > 0)
    if not hit.any(): return None
    return float(.3 - tt[hit].min())


for key in ('super90', 'm870'):
    v, t = tri_mesh(key, D[key])
    print('==', key, 'underside y at x=0 (z: y):', [(z, None if (y := underside(v, t, 0., z)) is None else round(y, 4)) for z in np.round(np.arange(-.03, .13, .01), 3)])
    print('   at x=+-0.012:', [(z, underside(v, t, .012, z) and round(underside(v, t, .012, z), 4), underside(v, t, -.012, z) and round(underside(v, t, -.012, z), 4)) for z in (0., .02, .04, .06, .08, .1)])
