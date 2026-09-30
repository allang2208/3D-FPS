"""Seated-pose helper (plain CPython / Blender Python): A762 runtime geometry as rendered.

The runtime mesh stores bind-pose vertices. Parts bound to bones other than WPN_root
(magazine, bolt, trigger, sights, charging handle) are drawn at D_bone @ v relative to
the receiver in the idle pose; D comes from Bake/seated_pose.json (probe_seated_pose.py,
A_A762_idle frame 0, Blender armature metres) and the dominant bone per vertex from
inspect/geometry/A762_bones.json (dump_bone_binding.py).
"""
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
GEOMETRY = HERE.parent / 'inspect' / 'geometry'
ARM_KEYS = ('Manny', 'BarePalm', 'BareNative', 'BareFamily')


def read_geometry(path):
    """Same layout as measure_references.read_geometry (kept PIL-free for Blender)."""
    with open(path, 'rb') as f:
        header = json.loads(f.readline().decode('utf-8'))
        V, T = header['vertices'], header['triangles']
        pos = np.fromfile(f, np.float32, V * 3).reshape(V, 3)
        tri = np.fromfile(f, np.int32, T * 3).reshape(T, 3)
        mat = np.fromfile(f, np.int32, T)
        uv = np.fromfile(f, np.float32, T * 6).reshape(T, 3, 2)
        nrm = np.fromfile(f, np.float32, T * 9).reshape(T, 3, 3)
    return header, pos, tri, mat, uv, nrm


def seat_points(points, bone):
    """Moves bind-pose points (UE cm) of one bone into the seated pose."""
    pose = json.loads((HERE / 'Bake' / 'seated_pose.json').read_text(encoding='utf-8'))
    if bone not in pose['bones']:
        return np.asarray(points, np.float64)
    D = np.array(pose['bones'][bone])
    flip = np.array([0.01, -0.01, 0.01])
    p = np.asarray(points, np.float64) * flip
    return (p @ D[:3, :3].T + D[:3, 3]) / flip


def load(key='A762_AfterSurface'):
    """Returns header, bind positions, seated positions (UE cm), triangles, material ids,
    dominant bone name per vertex and a gun-triangle mask."""
    h, pos, tri, mat, uv, nrm = read_geometry(GEOMETRY / (key + '.bin'))
    own = GEOMETRY / (key + '_bones.json')
    bones = json.loads((own if own.exists() else GEOMETRY / 'A762_bones.json').read_text(encoding='utf-8'))
    pose = json.loads((HERE / 'Bake' / 'seated_pose.json').read_text(encoding='utf-8'))
    dom = np.array(bones['dominant'])
    if len(dom) != len(pos):
        raise RuntimeError('bone dump does not match geometry dump (%d vs %d)' % (len(dom), len(pos)))
    names = bones['bones']
    seated = pos.astype(np.float64).copy()
    flip = np.array([0.01, -0.01, 0.01])
    for b, d in pose['bones'].items():
        if b not in names:
            continue
        sel = dom == names.index(b)
        if not sel.any():
            continue
        D = np.array(d)
        p = pos[sel].astype(np.float64) * flip  # UE cm -> Blender armature m
        q = p @ D[:3, :3].T + D[:3, 3]
        seated[sel] = q / flip
    bone_of = np.array([names[i] if i >= 0 else '' for i in dom])
    gun = ~np.array([any(k in (m or '') for k in ARM_KEYS) for m in h['materials']])[mat]
    return h, pos, seated, tri, mat, bone_of, gun
