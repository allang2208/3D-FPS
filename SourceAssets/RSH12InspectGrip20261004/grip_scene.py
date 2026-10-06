"""Current saved RSH mesh/profile and complete mixed-weight V7 hand geometry."""
import bpy, json, sys
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion
from mathutils.bvhtree import BVHTree
O = Path(__file__).parent
P = O.parents[1]
PREVIOUS = O.parent / 'RSH12Speedloader20261003'
sys.path.insert(0, str(O.parent / 'RSH12Grip20261003'))
from pose_geometry import matrix, packed, applied, native_pose, set_pose, track_at

def load(side='single'):
    src = PREVIOUS / ('Single' if side == 'single' else 'Dual/' + side)
    bpy.ops.wm.open_mainfile(filepath=str(src / ('RSH12_' + side + '_Editable.blend')))
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    rig.animation_data_clear()
    rig.data.pose_position = 'POSE'
    data = json.loads((O.parent / 'RSH12Grip20261003' / ('native_' + side + '.json')).read_text())
    data['clips'].update(json.loads((PREVIOUS / ('speed_' + side + '.json')).read_text())['clips'])
    profile = json.loads((src / 'profile.json').read_text())
    meta = json.loads((src / 'authoring.json').read_text())
    return rig, data, profile, meta

def pose(rig, data, profile, kind, sample):
    entry = next(e for e in profile['clips'] if e['kind'] == kind)
    return native_pose(rig, data, applied({n: matrix(v) for n, v in sample['local'].items()}, entry, sample['time']))

class Skin:
    def __init__(self, rig, side):
        self.rig = rig
        self.rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
        self.names = list(self.rest)
        ob = next(o for o in bpy.data.objects if o.type == 'MESH')
        groups = {g.index: g.name for g in ob.vertex_groups}
        points, weights, labels = [], [], []
        for v in ob.data.vertices:
            ww = [(groups[g.group], g.weight) for g in v.groups if groups[g.group] in self.rest and g.weight > 0.]
            label = max(ww, key=lambda a: a[1])[0] if ww else ''
            if label.endswith('_' + side) and label.startswith(('hand', 'thumb', 'index', 'middle', 'ring', 'pinky')):
                points.append(rig.matrix_world.inverted() @ ob.matrix_world @ v.co)
                weights.append(dict(ww))
                labels.append(label)
        self.labels = np.array(labels)
        self.used = sorted({n for ww in weights for n in ww})
        self.coords = np.array([[*p, 1.] for p in points])
        self.weights = np.array([[ww.get(n, 0.) for n in self.used] for ww in weights])
        self.weights /= self.weights.sum(axis=1)[:, None]
        self.bind = np.array([self.rest[n].inverted() for n in self.used])
        self.bound = np.einsum('bij,pj->bpi', self.bind, self.coords)

    def points(self, p, canonical):
        matrices = np.array([canonical @ p[n] for n in self.used])
        return np.einsum('bij,bpj,pb->pi', matrices, self.bound, self.weights, optimize=True)[:, :3]

def grip_trees():
    closed=O/'solid_9_l.json'
    if closed.exists():
        part=json.loads(closed.read_text())
        return [('9_l',BVHTree.FromPolygons([Vector(v) for v in part['verts']],part['faces']))]
    raw = json.loads((O.parent / 'RSH12Integration20261003/canonical_parts.json').read_text())
    # Solid grip only: do not mistake hollow cylinder/triggerguard parity for grip material.
    return [(part['name'], BVHTree.FromPolygons([Vector(v) for v in part['verts']], part['faces'])) for part in raw if part['name'] == '9_l']

RAY = Vector((.371, .691, .591)).normalized()
def signed(tree, pt):
    nearest, normal, _, distance = tree.find_nearest(Vector(pt))
    votes=0
    for direction in (RAY,Vector((.631,-.413,.653)).normalized(),Vector((-.533,.719,-.446)).normalized()):
        origin = Vector(pt) + direction * 1e-7
        hits = 0
        for _ in range(24):
            hit, _, _, _ = tree.ray_cast(origin, direction, .5)
            if hit is None: break
            hits += 1
            origin = hit + direction * 1e-6
        votes+=hits%2
    return distance * (-1 if votes>=2 else 1)

def canonical_pose(p, meta):
    return (p['WPN_root'] @ Matrix(meta['alignment'])).inverted()

def report(skin, p, meta, tree):
    points = skin.points(p, canonical_pose(p, meta))
    distances = np.array([signed(tree, v) for v in points]) * 1000
    result = {}
    for finger in ('hand', 'thumb', 'index', 'middle', 'ring', 'pinky'):
        d = distances[np.char.startswith(skin.labels, finger)]
        result[finger] = dict(vertices=int(len(d)), inside_half_mm=int((d < -.5).sum()), deepest_mm=float(max(0., -d.min())), nearest_mm=float(np.abs(d).min()))
    return result, points, distances
