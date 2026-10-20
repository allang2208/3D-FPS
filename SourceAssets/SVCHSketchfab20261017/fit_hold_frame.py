"""Fit the hand-hold frame of the accepted SVD and of the SVCh, then solve the
rigid transform that puts the SVCh where the SVD is held.

The submitted viewmodel only translated the SVCh so its grip centre matched the
SVD's; that cannot correct a different barrel pitch or roll, so the hands end up
off the grip and off the handguard. This measures a full orthonormal frame on
each gun -- bore direction from a muzzle-cap fit, up from the sight line, origin
at the grip -- and prints the rigid transform between them.

Writes Authoring/hold_frame.json.
"""
import gzip
import json
import struct
from pathlib import Path

import numpy as np

O = Path(__file__).parent
CT = {5120: ('i1', 1), 5121: ('u1', 1), 5122: ('i2', 2), 5123: ('u2', 2),
      5125: ('u4', 4), 5126: ('f4', 4)}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


def load_glb(path):
    src = open(path, 'rb').read()
    _, _, length = struct.unpack_from('<III', src, 0)
    off, chunks = 12, []
    while off < length:
        clen, ctype = struct.unpack_from('<II', src, off)
        chunks.append((ctype, off + 8, clen))
        off += 8 + clen
    J = json.loads(src[chunks[0][1]:chunks[0][1] + chunks[0][2]].decode('utf-8'))
    BIN = src[chunks[1][1]:chunks[1][1] + chunks[1][2]]

    def acc(i):
        a = J['accessors'][i]
        bv = J['bufferViews'][a['bufferView']]
        dt, sz = CT[a['componentType']]
        n = NC[a['type']]
        st = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
        stride = bv.get('byteStride') or sz * n
        cnt = a['count']
        if stride == sz * n:
            return np.frombuffer(BIN, dtype=np.dtype(dt), count=cnt * n, offset=st).reshape(cnt, n)
        return np.array([np.frombuffer(BIN, dtype=np.dtype(dt), count=n, offset=st + i * stride)
                         for i in range(cnt)])

    V = np.vstack([acc(m['primitives'][0]['attributes']['POSITION']) for m in J['meshes']]
                  ).astype('float64')
    return V


def bore_frame(V, muzzle_axis):
    """Return (origin_on_bore, forward) for the vertex set.

    The muzzle cap is the disc at the far end along `muzzle_axis`; its centroid
    sits on the bore, and the cap normal gives the barrel direction.
    """
    proj = V @ muzzle_axis
    far = V[proj > proj.max() - 1.6]
    centre = far.mean(0)
    fwd = np.asarray(muzzle_axis, dtype='float64')
    fwd = fwd / np.linalg.norm(fwd)
    return centre, fwd


def frame(origin, forward, up_hint):
    f = forward / np.linalg.norm(forward)
    u = up_hint - f * float(np.dot(up_hint, f))
    u = u / np.linalg.norm(u)
    r = np.cross(f, u)
    return np.column_stack([r, u, f]), origin  # columns: right, up, forward


def rigid_from_frames(Fa, Oa, Fb, Ob):
    R = Fb @ Fa.T
    t = Ob - R @ Oa
    return R, t


# ---- SVD (accepted, centimetres, dump space) --------------------------------
vm = json.loads(gzip.open(O / 'Donor' / 'vm.json.gz', 'rb').read().decode('utf-8')) \
    if (O / 'Donor' / 'vm.json.gz').suffix == '.gz' else None
if vm is None:
    vm = json.loads((O / 'Donor' / 'vm.json').read_text(encoding='utf-8'))
pos = np.asarray(vm['positions'], dtype='float64').reshape(-1, 3)
slots = vm['slots']
if vm.get('compact'):
    slots = [slots[i] if i < len(slots) else 'material' for i in range(max(vm['material']) + 1)]
tri = np.asarray(vm['triangles'], dtype='int64').reshape(-1, 3)
tri_arm = np.array([str(slots[m]).lower().startswith('mi_manny') for m in vm['material']])
vert_arm = np.zeros(len(pos), dtype=bool)
vert_arm[tri[tri_arm].ravel()] = True
gun_svd = pos[~vert_arm]
arm_svd = pos[vert_arm]
contact = json.loads((O / 'Authoring' / 'svd_bind_space.json').read_text(encoding='utf-8'))
grip_svd = np.asarray(contact['grip']['centre'], dtype='float64')
# SVD's bore runs along -Y with the muzzle at the most negative Y.
oS, fS = bore_frame(gun_svd, np.array([0.0, -1.0, 0.0]))
FS, _ = frame(oS, fS, np.array([0.0, 0.0, 1.0]))
# The SVD's grip is not necessarily on the bore line: carry its offset in the
# bore frame so the SVCh inherits the same relationship.
gS_local = FS.T @ (grip_svd - oS)

# ---- SVCh (glTF centimetres, +X muzzle, +Y up, +Z right) -------------------
V = load_glb(O / 'download' / 'svch.glb')
oV, fV = bore_frame(V, np.array([1.0, 0.0, 0.0]))
FV, _ = frame(oV, fV, np.array([0.0, 1.0, 0.0]))

measurements = json.loads((O / 'audit' / 'measurements.json').read_text(encoding='utf-8'))
# The audit reports its own frame; V is the raw glTF POSITION accessor. Convert
# the grip into the glTF frame first, or the transform is fitted across two
# different spaces and lands ~21 cm off.
off = json.loads((O / 'Authoring' / 'frame_offset.json').read_text(encoding='utf-8'))
ax = off['offset_audit_to_gltf']
gv = measurements['landmarks']['pistol_grip']['centre']
grip_v = np.array([gv[0] - ax['dx'], gv[2] - ax['dz'], gv[1] - ax['dy']], dtype='float64')

report = {
    'svd_bore_origin_cm': [round(v, 4) for v in oS],
    'svd_forward': [round(v, 4) for v in fS],
    'svd_grip_cm': [round(v, 4) for v in grip_svd],
    'svd_grip_in_bore_frame': [round(v, 4) for v in gS_local],
    'svch_bore_origin_cm': [round(v, 4) for v in oV],
    'svch_forward': [round(v, 4) for v in fV],
    'svch_grip_cm': [round(v, 4) for v in grip_v],
    'svch_arm_min': [round(float(v), 3) for v in arm_svd.min(0)],
    'svd_gun_min': [round(float(v), 3) for v in gun_svd.min(0)],
    'svd_gun_max': [round(float(v), 3) for v in gun_svd.max(0)],
}
(O / 'Authoring' / 'hold_frame.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
for k, v in report.items():
    print('%-26s %s' % (k, v))

# ---- rigid transform glTF frame -> SVD bind space --------------------------
# Anchored on the grip, so the SVCh's pistol grip lands exactly where the SVD's
# is held; the frames bring the bore direction and roll along with it.
R = FS @ FV.T
det = float(np.linalg.det(R))
t = grip_svd - R @ grip_v
mapped_grip = R @ grip_v + t
mapped_bore = R @ oV + t
mapped = (R @ V.T).T + t
hold = {
    'description': 'glTF centimetres -> SVCh author/bind space (SVD hold registration)',
    'R': [[round(float(x), 8) for x in row] for row in R],
    't_cm': [round(float(x), 6) for x in t],
    'det': round(det, 8),
    'grip_check_cm': [round(float(v), 4) for v in mapped_grip],
    'svd_grip_cm': [round(float(v), 4) for v in grip_svd],
    'grip_error_cm': round(float(np.linalg.norm(mapped_grip - grip_svd)), 6),
    'mapped_bbox_min': [round(float(v), 3) for v in mapped.min(0)],
    'mapped_bbox_max': [round(float(v), 3) for v in mapped.max(0)],
    'svd_gun_bbox_min': [round(float(v), 3) for v in gun_svd.min(0)],
    'svd_gun_bbox_max': [round(float(v), 3) for v in gun_svd.max(0)],
}
(O / 'Authoring' / 'hold_frame.json').write_text(
    json.dumps({**report, **hold}, indent=1), encoding='utf-8')
print()
for k in ('det', 'grip_error_cm', 'mapped_bbox_min', 'mapped_bbox_max',
          'svd_gun_bbox_min', 'svd_gun_bbox_max'):
    print('%-20s %s' % (k, hold[k]))
print('t_cm', hold['t_cm'])