"""Plan the A762 magazine-junction geometry repair (plain CPython). Writes Bake/magwell_repair.json.

All defects are in the original Meshy receiver/trigger (Refinement02 cut them around the
rebuilt magazine). They only show in the seated idle pose, where the rebuilt magazine sits
inside the fixed magwell collar (collar x 3.90..6.93, y -28.07..-20.27); in bind pose the
magazine, bolt and trigger are displaced (seated.py).
A. Collar teeth: cut-border slivers of the receiver hang below the collar onto the magazine
   top. The collar is rolled: its bottom is z -6.84 at the left wall (x 3.95) and -6.58 at
   the right wall (x 6.93). Low tooth vertices are lifted 0.04 cm above that plane, behind
   the collar walls; the side-wall triangles above stay closed (no holes).
B. Old magwell remnants that reach forward past the magazine rear face (y < -20.15) into the
   magazine: deleted (the magazine and its rear catch occupy that space).
C. Needle shards around the magazine catch and along the trigger slot behind it
   (y -20.6..-15.5, below the collar): long, needle-thin receiver triangles
   (longest edge > 0.25 cm, longest^2/(2*area) > 8).
D. Rebuilt magazine catch: the ragged old housing, catch lever and shards between the
   magazine rear catch and the trigger guard (receiver triangles with centroid in
   CATCH_ZONE/OLD_SIDES, and the whole trigger slot, which is only debris there) are deleted
   and replaced by closed rebuilt parts: a full-width rear magwell wall continuing the
   receiver's lower edge, a narrower catch body below it that the trigger guard ends on, a
   pivot rivet on each side, a catch lever with a paddle and a short socket for the cut
   front end of the trigger guard (same FrontAssembly_Rebuilt slot
   and WPN_root binding as the collar). UV0 is planar at the FrontAssembly texel density;
   UV1 points at a neutral mask texel (edge 0, cavity 0, AO 1); UV2/UV3 are zero like the
   other gun triangles.
E. Bolt-carrier flap: the part of the Meshy bolt slot seated in front of the charging-handle
   knob (y < -32.6) is a jagged plate standing out over the handguard; deleted. The knob and
   the carrier seen in the ejection port stay.
Indices refer to inspect/geometry/A762_AfterSurface.bin (= fresh Geometry Script copy).
"""
import json
import math
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import seated  # noqa: E402

TEETH_Y = (-29.5, -20.25)
REMNANT = {'y': (-21.8, -20.15), 'z': (-10.2, -6.86), 'x': (3.6, 7.2)}
REAR_WALL = {'x': (3.98, 6.86), 'y': (-20.20, -16.20), 'z': (-8.45, -7.25)}
# The lever tip stays at the old Meshy lever depth (z about -11.7): the empty-reload hand
# pose (IndexClearance) was tuned against it.
CATCH_BODY = {'x': (4.55, 6.30), 'y': (-20.10, -17.55), 'z': (-11.40, -8.43)}
CATCH_ZONE = {'x': (3.6, 7.2), 'y': (-20.6, -19.05), 'z': (-12.0, -7.25)}
OLD_SIDES = {'x': (3.6, 7.2), 'y': (-20.2, -17.95), 'z': (-11.9, -8.45)}
LEVER = {'x': (5.00, 5.85), 'y': (-20.05, -19.70), 'z': (-11.62, -11.38)}
PADDLE = {'x': (4.80, 6.05), 'y': (-20.15, -19.60), 'z': (-11.75, -11.60)}
# Short socket that takes the cut front end of the trigger guard below the catch body.
GUARD_SOCKET = {'x': (4.85, 6.00), 'y': (-17.95, -17.25), 'z': (-11.78, -11.20)}
RIVET = {'y': -19.25, 'z': -9.85, 'radius': 0.22, 'height': 0.07, 'segments': 16}
NEUTRAL_UV1 = (0.7002, 0.1494)


def collar_bottom(x):
    """Bottom plane of the fixed magwell collar (measured on its long wall faces)."""
    return -6.84 + (np.clip(x, 3.95, 6.93) - 3.95) / (6.93 - 3.95) * 0.26


h, pos, st, tri, mat, bone, gun = seated.load()
slot = {n: i for i, n in enumerate(h['slots'])}
rec, trig = slot['M_A762_Receiver'], slot['M_A762_Trigger']
P = st[tri]
C = P.mean(1)
area = 0.5 * np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1)
inside = lambda c, box, pad=0.0: np.all([(c[:, k] > box[a][0] - pad) & (c[:, k] < box[a][1] + pad)
                                         for k, a in enumerate('xyz')], axis=0)

# A. Lift receiver vertices below the collar in its span (root-bound: bind == seated).
# Only vertices used by receiver triangles alone are moved.
rec_v = np.setdiff1d(np.unique(tri[mat == rec]), np.unique(tri[mat != rec]))
root_v = rec_v[bone[rec_v] == 'WPN_root']
p = pos[root_v]
teeth_v = root_v[(p[:, 2] < collar_bottom(p[:, 0]) - 0.005) & (p[:, 1] > TEETH_Y[0]) & (p[:, 1] < TEETH_Y[1])
                 & (p[:, 0] > 3.6) & (p[:, 0] < 7.2)]
# The old magwell rear below the collar end is handled by B-D, not lifted.
teeth_v = teeth_v[~((pos[teeth_v, 1] > -20.9) & (pos[teeth_v, 2] < -7.3))]
move = {int(v): [float(pos[v, 0]), float(pos[v, 1]), float(collar_bottom(pos[v, 0]) + 0.04)] for v in teeth_v}
users = np.isin(tri, np.array(list(move), dtype=np.int64)).any(1)
assert np.all(mat[users] == rec), 'moved vertex shared with another slot'

# B-D deletions (seated coordinates; the trigger is on its own bone).
E = np.stack([np.linalg.norm(P[:, (k + 1) % 3] - P[:, k], axis=1) for k in range(3)], 1)
needle = (E.max(1) > 0.25) & (E.max(1) ** 2 / np.maximum(2 * area, 1e-12) > 8)
remnant = inside(C, REMNANT)
around_catch = inside(C, {'x': REMNANT['x'], 'y': (-20.6, -15.5), 'z': (-10.6, -6.86)}) & needle
old_catch = inside(C, CATCH_ZONE) | inside(C, OLD_SIDES) | inside(C, REAR_WALL, 0.03) | inside(C, CATCH_BODY, 0.03)
bolt_flap = (mat == slot['M_A762_Bolt']) & (C[:, 1] < -32.6)
# The whole trigger slot is Meshy debris around the old catch (the trigger blade itself is
# part of the receiver slot); what is left after the zones is a flat jagged plate.
delete = np.nonzero(((remnant | around_catch | old_catch) & (mat == rec)) | (mat == trig) | bolt_flap)[0]

# D. Housing block and rivets (UE cm, WPN_root: bind == seated).
layout = json.loads((HERE / 'uv_layout.json').read_text(encoding='utf-8'))
uv_per_cm = layout['A762']['slots']['M_A762_FrontAssembly_Rebuilt']['uv_per_cm']
verts, tris, normals, uv0 = [], [], [], []


def planar_uv(point, n):
    a, b = [k for k in range(3) if abs(n[k]) < 0.9] if max(abs(c) for c in n) > 0.9 else (1, 2)
    return [point[a] * uv_per_cm, point[b] * uv_per_cm]


def add_polygon(points, n):
    """Fan-triangulates a convex polygon; the dump winding has the right-handed cross
    product pointing inward (UE is left-handed), so orient against the outward normal."""
    q = np.array(points)
    if np.dot(np.cross(q[1] - q[0], q[2] - q[0]), n) > 0:
        points = points[::-1]
    base = len(verts)
    verts.extend([list(map(float, p)) for p in points])
    normals.extend([list(map(float, n))] * len(points))
    uv0.extend(planar_uv(p, n) for p in points)
    tris.extend([[base, base + i, base + i + 1] for i in range(1, len(points) - 1)])


def add_box(box):
    lo = [box[a][0] for a in 'xyz']
    hi = [box[a][1] for a in 'xyz']
    for axis in range(3):
        a, b = [k for k in range(3) if k != axis]
        for sign in (-1, 1):
            quad = []
            for ua, ub in ((0, 0), (1, 0), (1, 1), (0, 1)):
                pt = [0.0] * 3
                pt[axis] = hi[axis] if sign > 0 else lo[axis]
                pt[a] = hi[a] if ua else lo[a]
                pt[b] = hi[b] if ub else lo[b]
                quad.append(pt)
            n = [0.0] * 3
            n[axis] = float(sign)
            add_polygon(quad, n)


def add_rivet(x_face, outward):
    """Short cylinder along X standing on a housing side face, with a flat cap."""
    ring = [(RIVET['y'] + RIVET['radius'] * math.cos(2 * math.pi * i / RIVET['segments']),
             RIVET['z'] + RIVET['radius'] * math.sin(2 * math.pi * i / RIVET['segments'])) for i in range(RIVET['segments'])]
    x0, x1 = x_face - outward * 0.02, x_face + outward * RIVET['height']
    for i in range(RIVET['segments']):
        (y0, z0), (y1, z1) = ring[i], ring[(i + 1) % RIVET['segments']]
        mid = math.pi * 2 * (i + 0.5) / RIVET['segments']
        add_polygon([[x0, y0, z0], [x0, y1, z1], [x1, y1, z1], [x1, y0, z0]], [0.0, math.cos(mid), math.sin(mid)])
    add_polygon([[x1, y, z] for y, z in ring], [float(outward), 0.0, 0.0])


add_box(REAR_WALL)
add_box(CATCH_BODY)
add_box(LEVER)
add_box(PADDLE)
add_box(GUARD_SOCKET)
add_rivet(CATCH_BODY['x'][0], -1)
add_rivet(CATCH_BODY['x'][1], 1)
collar_v = np.unique(tri[mat == slot['M_A762_FrontAssembly_Rebuilt']])
donor = int(collar_v[np.argmin(np.linalg.norm(pos[collar_v] - np.array([5.4, -20.3, -6.84]), axis=1))])
assert bone[donor] == 'WPN_root'
parts = [{'name': 'A762_WS_MagCatchHousing', 'slot': 'M_A762_FrontAssembly_Rebuilt', 'bone_donor_vertex': donor,
          'vertices': verts, 'triangles': tris, 'normals': normals, 'uv0': uv0, 'uv1': NEUTRAL_UV1}]

per = {h['slots'][i]: {'triangles': int((mat[delete] == i).sum()), 'area_cm2': round(float(area[delete][mat[delete] == i].sum()), 3)}
       for i in (rec, trig, slot['M_A762_Bolt'])}
out = {'source': 'inspect/geometry/A762_AfterSurface.bin', 'triangle_count': int(len(tri)), 'vertex_count': int(len(pos)),
       'position_checksum': float(np.abs(pos.astype(np.float64)).sum()),
       'move_vertices': move, 'delete_triangles': delete.tolist(), 'add_parts': parts,
       'delete_centroid_checksum': float((pos[tri[delete]].astype(np.float64).mean(1) @ np.array([1.0, 2.0, 3.0])).sum()),
       'summary': {'lifted_vertices': len(move),
                   'lift_max_cm': round(float(max(m[2] - pos[v, 2] for v, m in move.items())), 3) if move else 0,
                   'triangles_touching_lifted': int(users.sum()), 'deleted': per,
                   'added_vertices': len(verts), 'added_triangles': len(tris)}}
(HERE / 'Bake' / 'magwell_repair.json').write_text(json.dumps(out), encoding='utf-8')
print('MAGWELL_REPAIR_PLAN', json.dumps(out['summary']))
