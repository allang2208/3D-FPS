"""Fold impact using the correct global-vertex-id mapping."""
from pathlib import Path
import json
import numpy as np

W = Path(__file__).resolve().parents[2] / "SourceAssets/BareSkinV9M4_20261017/Work"
pay = json.load(open(W / "install_payload.json"))
weights = {int(k): v for k, v in pay['weights'].items()}
vids = np.asarray(pay['vertex_ids'], dtype=np.int64)
pos = np.asarray(pay['positions'], dtype=float).reshape(-1, 3)
T = np.asarray(pay['triangle_ids'], dtype=np.int64).reshape(-1, 3)
local = {g: i for i, g in enumerate(vids)}

ARM_KEYS = ('clavicle', 'upperarm', 'lowerarm', 'hand', 'thumb', 'index',
            'middle', 'ring', 'pinky')


def is_arm(name):
    n = name.lower()
    return any(k in n for k in ARM_KEYS)


print('verts %d  tris %d  weights %d' % (len(vids), len(T), len(weights)))

bones = sorted({b for v in weights.values() for b in v})
nonarm = [b for b in bones if not is_arm(b)]
print('\ndistinct bones in weight data: %d' % len(bones))
print('NON-ARM bones: %s' % (nonarm if nonarm else 'NONE'))

if nonarm:
    print('\nvertices touching a non-arm bone:')
    for b in nonarm:
        vs = [g for g, v in weights.items() if b in v]
        print('   %-24s %d verts' % (b, len(vs)))

# arm-only check on every vertex that has weights
mixed = 0
for g, infl in weights.items():
    if any(not is_arm(b) for b in infl):
        mixed += 1
print('\nvertices with ANY non-arm influence: %d' % mixed)

# triangles that include such a vertex
if mixed:
    bad = set(g for g, infl in weights.items() if any(not is_arm(b) for b in infl))
    bad_local = {local[g] for g in bad if g in local}
    n_tri = sum(1 for t in T if any(int(v) in bad_local for v in t))
    print('triangles touching those vertices: %d of %d (%.1f%%)'
          % (n_tri, len(T), 100.0 * n_tri / len(T)))
