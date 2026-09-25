"""Shared helpers: express a left-hand grip as a relation to the magazine shell.

The grip is stored in a frame built from the magazine's own rest geometry:

* ``l`` - local long axis of the shell at the grip height (from the spine fit),
  signed to point from the floorplate towards the feed end;
* ``w`` - the wider in-plane axis of the shell cross-section;
* ``t`` - the thin axis, signed towards the palm side;
* origin - the centre of the shell box, expressed along ``l`` as a height.

Heights are reported as the distance from the floorplate, so the same grip can be
rebuilt on a longer magazine of a different cross-section without any hand-tuned
world offset.  A relation R maps magazine-frame coordinates to hand-bone world
matrices: ``hand_world = MagDeform @ Frame(h) @ R``.
"""
import bpy, math
from mathutils import Vector, Matrix

DIGITS = ['thumb', 'index', 'middle', 'ring', 'pinky']
HAND_CHAIN = ['hand_l'] + [f'{d}_{k}_l' for d in DIGITS
                           for k in ('metacarpal', '01', '02', '03')]
HAND_CHAIN = [n for n in HAND_CHAIN if n != 'thumb_metacarpal_l']


def pca(points):
    c = sum(points, Vector()) / len(points)
    cov = [[0.0] * 3 for _ in range(3)]
    for p in points:
        d = p - c
        for i in range(3):
            for j in range(3):
                cov[i][j] += d[i] * d[j]
    A = [row[:] for row in cov]
    vecs = []
    for _ in range(3):
        v = Vector((1.0, 0.31, 0.67))
        for _ in range(500):
            w = Vector((sum(A[i][j] * v[j] for j in range(3)) for i in range(3)))
            if w.length < 1e-14:
                break
            v = w.normalized()
        lam = sum(v[i] * sum(A[i][j] * v[j] for j in range(3)) for i in range(3))
        vecs.append((lam, v))
        for i in range(3):
            for j in range(3):
                A[i][j] -= lam * v[i] * v[j]
    vecs.sort(key=lambda x: -x[0])
    return c, [v for _, v in vecs]


def shell_points(rig, mag, group='WPN_SOCKET_Magazine'):
    names = [g.name for g in mag.vertex_groups]
    gi = mag.vertex_groups[group].index if group in names else None
    out = []
    for v in mag.data.vertices:
        if gi is None:
            out.append(mag.matrix_world @ v.co); continue
        w = 0.0
        for g in v.groups:
            if g.group == gi:
                w = g.weight
        if w > 0.5:
            out.append(mag.matrix_world @ v.co)
    return out


def deform(rig, pose, bone='WPN_SOCKET_Magazine'):
    rest = rig.data.bones[bone].matrix_local
    return rig.matrix_world @ pose[bone] @ rest.inverted() @ rig.matrix_world.inverted()


class Shell:
    """Local frame of a magazine shell, built from its rest geometry.

    ``up_dir`` (a direction, normally the clip's insertion direction) fixes the
    sign of the long axis so the frame means the same thing on every magazine:
    ``lo`` is the floorplate end and ``hi`` the feed end.
    """

    def __init__(self, points, well_hint=None, palm_hint=None, up_dir=None, slice_mm=14.0):
        self.points = points
        c, ax = pca(points)
        u = ax[0]
        ts = [p.dot(u) for p in points]
        lo, hi = min(ts), max(ts)
        n = max(8, int((hi - lo) * 1000 / 6.0))
        bins = [[] for _ in range(n)]
        for p, t in zip(points, ts):
            i = min(n - 1, int((t - lo) / max(1e-9, hi - lo) * n))
            bins[i].append(p)
        cents = [sum(b, Vector()) / len(b) for b in bins if len(b) >= 4]
        _, cax = pca(cents)
        l = cax[0].copy()
        if up_dir is not None:
            if l.dot(up_dir) < 0:
                l = -l
        elif well_hint is not None and l.dot(well_hint - c) < 0:
            l = -l
        self.l = l
        self.lo = min(p.dot(l) for p in points)
        self.hi = max(p.dot(l) for p in points)
        self.palm_hint = palm_hint
        self.slice = slice_mm / 1000.0

    @property
    def length(self):
        return self.hi - self.lo

    def height(self, point_rest):
        """Distance of a rest-space point from the floorplate end (metres)."""
        return point_rest.dot(self.l) - self.lo

    def frame_at_height(self, h):
        """Frame whose origin is the shell-box centre at height h above the floorplate."""
        target = self.lo + h
        pts = [p for p in self.points if abs(p.dot(self.l) - target) <= self.slice]
        if len(pts) < 6:
            pts = sorted(self.points, key=lambda p: abs(p.dot(self.l) - target))[:40]
        c = sum(pts, Vector()) / len(pts)
        rel = [p - c - self.l * (p - c).dot(self.l) for p in pts]
        _, ax = pca(rel)
        w = ax[0].copy()
        t = ax[2].copy()
        if t.dot(self.palm_hint - c) < 0:
            t = -t
        w = t.cross(self.l).normalized()
        t = self.l.cross(w).normalized()
        # centre in the thickness / width directions only
        origin = c + self.l * (target - c.dot(self.l))
        origin -= self.l * (origin - c).dot(self.l)
        origin = origin - t * (origin - c).dot(t) - w * (origin - c).dot(w)
        return self.l, w, t, origin

    def frame_matrix(self, h):
        l, w, t, o = self.frame_at_height(h)
        return Matrix(((l.x, w.x, t.x, o.x), (l.y, w.y, t.y, o.y),
                       (l.z, w.z, t.z, o.z), (0.0, 0.0, 0.0, 1.0)))

    def cross_section_mm(self, h):
        target = self.lo + h
        pts = [p for p in self.points if abs(p.dot(self.l) - target) <= self.slice]
        if not pts:
            return None
        _, w, t, o = self.frame_at_height(h)
        ws = [(p - o).dot(w) for p in pts]
        ts = [(p - o).dot(t) for p in pts]
        return (max(ws) - min(ws)) * 1000, (max(ts) - min(ts)) * 1000


def hand_world(rig, pose):
    return {n: rig.matrix_world @ pose[n] for n in HAND_CHAIN}


def knuckle_rest(rig, pose, D):
    hw = hand_world(rig, pose)
    k = sum((hw[f'{d}_01_l'].translation for d in DIGITS[1:]), Vector()) / 4
    return D.inverted() @ k


def aimed(old, old_end, origin, end):
    return Matrix.LocRotScale(origin,
                              (old_end - old.translation).rotation_difference(end - origin) @ old.to_quaternion(),
                              old.to_scale())


def solve_arm(rig, names, original, target, slack=0.004):
    """Clavicle rotation plus two-bone IK on the original arm; bone lengths kept."""
    p = dict(target)
    shoulder = original['upperarm_l'].translation
    elbow = original['lowerarm_l'].translation
    wrist = original['hand_l'].translation
    tgt = p['hand_l'].translation
    l1 = (elbow - shoulder).length
    l2 = (wrist - elbow).length
    if (tgt - shoulder).length > l1 + l2 - slack and 'clavicle_l' in original:
        clav = original['clavicle_l']; c = clav.translation
        R = (shoulder - c).length; Dst = (tgt - c).length
        axis_c = (tgt - c).normalized()
        cosine = max(-1.0, min(1.0, (R * R + Dst * Dst - (l1 + l2 - slack) ** 2) / (2 * R * Dst)))
        side = shoulder - c - axis_c * (shoulder - c).dot(axis_c)
        side.normalize()
        newshoulder = c + axis_c * (R * cosine) + side * (R * math.sqrt(max(0.0, 1 - cosine * cosine)))
        p['clavicle_l'] = aimed(clav, shoulder, c, newshoulder)
        shoulder = newshoulder
    axis = (tgt - shoulder).normalized()
    distance = min((tgt - shoulder).length, l1 + l2 - 1e-6)
    pole = elbow - shoulder - axis * (elbow - shoulder).dot(axis)
    pole.normalize()
    reach = (l1 * l1 - l2 * l2 + distance * distance) / (2 * distance)
    height = math.sqrt(max(0.0, l1 * l1 - reach * reach))
    ne = shoulder + axis * reach + pole * height
    du = aimed(original['upperarm_l'], elbow, shoulder, ne) @ original['upperarm_l'].inverted()
    dl = aimed(original['lowerarm_l'], wrist, ne, tgt) @ original['lowerarm_l'].inverted()
    for n in names:
        if n.endswith('_l') and n.startswith('upperarm'):
            p[n] = du @ original[n]
        elif n.endswith('_l') and n.startswith('lowerarm'):
            p[n] = dl @ original[n]
    return p


def apply_world(rig, target):
    """Write world-space bone matrices in hierarchy order; untouched bones keep
    their current (already evaluated) transform."""
    bones = [b.name for b in rig.pose.bones]
    parents = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    local = {n: rest[parents[n]].inverted() @ rest[n] if parents[n] else rest[n] for n in bones}
    order, done, todo = [], set(), list(bones)
    while todo:
        for n in list(todo):
            if parents[n] is None or parents[n] in done:
                order.append(n); done.add(n); todo.remove(n)
    for n in order:
        if n not in target:
            continue
        par = parents[n]
        pm = target[par] if par in target else (rig.pose.bones[par].matrix if par else None)
        m = target[n]
        rig.pose.bones[n].matrix_basis = local[n].inverted() @ (pm.inverted() @ m if par else m)
        bpy.context.view_layer.update()
