"""Fit the loader guide to the M870 receiver (offline). Writes guide.json (component-space cm mesh).

The SUPER90 guide (rectangular adapter under the loading port, R9 ContactR9) is
moved by the same port offset as the loader (DELTA) and its upper rim is refitted
to the M870 receiver underside (+0.35 mm bearing overlap, as on SUPER90); the
lower opening keeps its relation to the seated tube tip. Clearance against the
racked pump is checked.
"""
import json
from pathlib import Path
import numpy as np
from rig import row2m, inv
from analyze_guide import tri_mesh, underside, to_gun
from author_clips import DELTA

O = Path(__file__).parent
D = json.loads((O / 'inputs.json').read_text()); G = json.loads((O / 'geometry.json').read_text())
S, M = D['super90'], D['m870']
g = to_gun(np.array(G['super90_guide']['positions']), S)
tris = np.array(G['super90_guide']['triangles'])
vs, ts = tri_mesh('super90', S); vm, tm = tri_mesh('m870', M)
OVERLAP = .00035; XO = .0135
y_bottom = float(g[:, 1].max())


def rim(v, t, x, z):
    """Lowest receiver surface between the vertex and the side edge: never dips into the port opening."""
    ys = [y for y in (underside(v, t, x, z), underside(v, t, np.sign(x) * XO, z), underside(v, t, 0., z) if abs(x) < 1e-4 else None) if y is not None]
    return max(ys) - OVERLAP


new = g.copy(); s_rim = {}; m_rim = {}
for i, (x, y, z) in enumerate(g):
    kx = (round(x, 3), round(z, 3))
    if kx not in s_rim:
        s_rim[kx] = rim(vs, ts, x, z); m_rim[kx] = rim(vm, tm, x, z + DELTA[2])
    top_s = s_rim[kx]; top_m = m_rim[kx]
    s = np.clip((y - top_s) / max(y_bottom - top_s, 1e-6), 0, 1)
    new[i] = [x, y + DELTA[1] + (1 - s) * (top_m - (top_s + DELTA[1])), z + DELTA[2]]
# Penetration of the fitted guide into the receiver beyond the bearing overlap.
pen = []
for x, y, z in new[::7]:
    u = underside(vm, tm, x, z)
    if u is not None and y < u - .0015: pen.append((round(x, 4), round(y, 4), round(z, 4), round(u, 4)))
print('guide gun-frame bbox', new.min(0).round(4), new.max(0).round(4), 'deepest rim change mm', round(float(np.abs(new[:, 1] - g[:, 1] - DELTA[1]).max()) * 1000, 2))
print('vertices more than 1.5 mm inside the receiver (sampled):', len(pen), pen[:8])
# Racked pump clearance: WPN_bolt geometry at cycle peak (bolt +0.105 m back).
geo = G['m870']; vv = to_gun(np.array(geo['positions']), M); dom = np.array(geo['dominant'])
pump = vv[dom == 'WPN_bolt']; travel = .105
racked = pump + np.array([0, 0, travel])
lo, hi = new.min(0), new.max(0)
inside = racked[(racked[:, 0] > lo[0]) & (racked[:, 0] < hi[0]) & (racked[:, 1] > lo[1]) & (racked[:, 1] < hi[1]) & (racked[:, 2] > lo[2]) & (racked[:, 2] < hi[2])]
below = [p for p in inside if (u := underside(vm, tm, p[0], p[2] - travel)) is not None and p[1] > u + .0005]
print('pump vertices inside the guide box when racked:', len(inside), 'of which outside the receiver (visible clash):', len(below),
      'pump bbox (rest)', pump.min(0).round(3), pump.max(0).round(3))
print('  sample', np.round(inside[:6], 4).tolist())
root = row2m(M['ref_world']['WPN_root'])
comp = (root @ np.c_[new, np.ones(len(new))].T).T[:, :3]
(O / 'guide.json').write_text(json.dumps(dict(positions=comp.tolist(), triangles=tris.tolist(),
    material_paths=G['super90_guide']['material_paths'], delta_gun_m=DELTA.tolist(), overlap_m=OVERLAP,
    racked_pump_vertices_inside_box=int(len(inside)), penetrations_sampled=len(pen)), separators=(',', ':')))
