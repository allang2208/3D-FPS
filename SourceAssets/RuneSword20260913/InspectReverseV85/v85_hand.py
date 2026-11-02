"""V84 hand: authored finger shapes, V9 forearm twist, skin contact path and hilt clearance.

Fingers flex about their local Z (bone points along local -X, +Z is the radial/thumb side) and spread about
local Y. Twist bones follow the V9 rule: lowerarm_twist_01 carries 100 % and twist_02 50 % of the hand's
roll about the forearm, measured against lowerarm and the bind relation.
"""
import math

import numpy as np
from mathutils import Matrix, Quaternion, Vector



FINGERS = ('thumb', 'index', 'middle', 'ring', 'pinky')
HILT_R = 0.0175
IDLE_CURL = {'01': 48.0, '02': 48.0, '03': 36.0}
IDLE_CURL_THUMB = {'01': 0.0, '02': 24.0, '03': 24.0}
HILT_Z = (-0.25, -0.03)
GUARD = (0.182, 0.034, -0.03, 0.06)  # |x|, |y|, z range in WPN local


def finger_bones(side, parent):
    names = [f + '_' + j + '_' + side for f in FINGERS for j in ('metacarpal', '01', '02', '03')]
    names = [n for n in names if n in parent]
    order, seen = [], set()
    while len(order) < len(names):
        for n in names:
            if n not in seen and (parent[n] not in names or parent[n] in seen):
                order.append(n)
                seen.add(n)
    return order


def finger_locals(shape, local_rest, idle_local):
    """Right-hand finger locals from a shape: {finger: (curl, spread_deg)} with curl as a fraction of the idle
    grip per joint (01/02/03; thumb 01 also takes `thumb_oppose_deg` about local Z)."""
    out = {}
    for name, (loc_i, scale_i) in idle_local.items():
        finger, joint = name.split('_')[0], name.split('_')[1]
        if joint == 'metacarpal':
            rot = Quaternion()
        else:
            base = (IDLE_CURL_THUMB if finger == 'thumb' else IDLE_CURL)[joint]
            curl = shape[finger + '_' + joint]
            rot = Quaternion((0.0, 0.0, 1.0), math.radians(curl * base))
            if joint == '01':
                rot = Quaternion((0.0, 1.0, 0.0), math.radians(shape[finger + '_spread'])) @ rot
                if finger == 'thumb':
                    rot = Quaternion((0.0, 0.0, 1.0), math.radians(shape['thumb_oppose'])) @ rot
        out[name] = local_rest[name] @ Matrix.LocRotScale(loc_i, rot, scale_i)
    return out


class Twist:
    """V9 forearm twist for one side."""

    def __init__(self, rest, side):
        self.s = side
        self.lo, self.hand = 'lowerarm_' + side, 'hand_' + side
        self.bones = (('lowerarm_twist_01_' + side, 1.0), ('lowerarm_twist_02_' + side, 0.5))
        fd = (rest[self.hand].translation - rest[self.lo].translation).normalized()
        self.axis_l = (rest[self.lo].to_quaternion().inverted() @ fd).normalized()
        self.rel = {b: rest[self.lo].inverted() @ rest[b] for b, _ in self.bones}
        self.rel_hand = rest[self.lo].to_quaternion().inverted() @ rest[self.hand].to_quaternion()
        self.prev = None

    def roll(self, pose):
        q = (pose[self.lo].to_quaternion().inverted() @ pose[self.hand].to_quaternion()) @ self.rel_hand.inverted()
        if q.w < 0.0:
            q.negate()
        th = math.degrees(2.0 * math.atan2(Vector((q.x, q.y, q.z)).dot(self.axis_l), q.w))
        if self.prev is not None:
            th += 360.0 * round((self.prev - th) / 360.0)
        self.prev = th
        return th

    def apply(self, pose, scale):
        th = self.roll(pose)
        ql = pose[self.lo].to_quaternion()
        for b, share in self.bones:
            local_q = Quaternion(self.axis_l, math.radians(share * th)) @ self.rel[b].to_quaternion()
            pose[b] = Matrix.LocRotScale(pose[self.lo] @ self.rel[b].translation, ql @ local_q, scale[b])
        return th


class Skin:
    """Linear-blend skinning of selected V7 vertices (bind coordinates = rig space)."""

    def __init__(self, mesh, rest, ids):
        groups = {g.index: g.name for g in mesh.vertex_groups}
        self.bones = sorted({groups[g.group] for i in ids for g in mesh.data.vertices[i].groups
                             if groups[g.group] in rest and g.weight > 1e-4})
        col = {b: k for k, b in enumerate(self.bones)}
        self.V = np.array([list(mesh.data.vertices[i].co) for i in ids], dtype=np.float64)
        self.N = np.array([list(mesh.data.vertices[i].normal) for i in ids], dtype=np.float64)
        W = np.zeros((len(ids), len(self.bones)))
        for r, i in enumerate(ids):
            for g in mesh.data.vertices[i].groups:
                name = groups[g.group]
                if name in col:
                    W[r, col[name]] += g.weight
        W /= np.maximum(W.sum(axis=1, keepdims=True), 1e-9)
        self.W = W
        self.rest_inv = [np.array(rest[b].inverted()) for b in self.bones]

    def posed(self, pose):
        P = np.zeros_like(self.V)
        N = np.zeros_like(self.N)
        for k, b in enumerate(self.bones):
            w = self.W[:, k:k + 1]
            if not w.any():
                continue
            M = np.array(pose[b]) @ self.rest_inv[k]
            P += w * (self.V @ M[:3, :3].T + M[:3, 3])
            N += w * (self.N @ M[:3, :3].T)
        N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)
        return P, N


def hilt_depth(wpn, pts, z_range=HILT_Z, radius=HILT_R):
    """Per point: penetration into the hilt cylinder (m, > 0 inside) and the local radial direction."""
    inv = np.array(wpn.inverted())
    L = pts @ inv[:3, :3].T + inv[:3, 3]
    d = np.hypot(L[:, 0], L[:, 1])
    inside = (L[:, 2] > z_range[0]) & (L[:, 2] < z_range[1])
    pen = np.where(inside, radius - d, -1.0)
    radial = np.stack([L[:, 0], L[:, 1], np.zeros(len(L))], axis=1) / np.maximum(d, 1e-9)[:, None]
    return pen, radial


def push_clear(wpn, pts, iterations=4, allow=0.0015):
    """Translate the sword out of the hand vertices it penetrates; returns the new matrix and residual depth."""
    for _ in range(iterations):
        pen, radial = hilt_depth(wpn, pts)
        mask = pen > allow
        if not mask.any():
            return wpn, float(max(pen.max(), 0.0))
        push = -(radial[mask] * pen[mask][:, None]).sum(axis=0)
        n = np.linalg.norm(push)
        if n < 1e-9:
            break
        step = Vector((push / n) * (pen[mask].max() - allow + 0.0005))
        world = wpn.to_3x3() @ step
        wpn = Matrix.Translation(world) @ wpn
    pen, _ = hilt_depth(wpn, pts)
    return wpn, float(max(pen.max(), 0.0))


class SwordField:
    """Signed distance to the real sword mesh in WPN_root local space (BVH nearest + face normal sign)."""

    def __init__(self, sword, rest_wpn):
        from mathutils.bvhtree import BVHTree
        to_local = rest_wpn.inverted() @ sword.matrix_world
        verts = [to_local @ v.co for v in sword.data.vertices]
        self.bvh = BVHTree.FromPolygons(verts, [tuple(p.vertices) for p in sword.data.polygons])

    def depths(self, wpn, pts, hilt_only=False):
        """(depth m > 0 inside, outward normal in WPN local, local z) per point."""
        inv = wpn.inverted()
        out = []
        for p in pts:
            L = inv @ Vector(p)
            if hilt_only and L.z > HILT_Z[1]:
                out.append((-1.0, None, L.z))
                continue
            loc, n, _, dist = self.bvh.find_nearest(L, 0.05)
            if loc is None:
                out.append((-1.0, None, L.z))
                continue
            inside = (L - loc).dot(n) < 0.0
            out.append((dist if inside else -dist, n, L.z))
        return out

    def push(self, wpn, pts, allow=0.004, iterations=6, max_move=0.04, axis=None):
        """Move the sword out of the hand/forearm along the real surface normals (only along `axis`, world,
        when given). A step that does not reduce the summed overlap is undone, so two-sided contact
        (web vs thumb) cannot run away."""
        def overlap(m):
            rows = self.depths(m, pts)
            hit = [(d, n) for d, n, _ in rows if d > allow]
            return sum(d - allow for d, _ in hit), hit, max([d for d, _, _ in rows] + [0.0])

        start = wpn.translation.copy()
        cost, hit, worst = overlap(wpn)
        for _ in range(iterations):
            if not hit:
                break
            acc = Vector()
            for d, n in hit:
                acc += n * (d - allow)
            if acc.length < 1e-9:
                break
            move = wpn.to_3x3() @ (-acc.normalized())
            if axis is not None:
                along = move.dot(axis)
                if abs(along) < 0.2:
                    break
                move = axis * (1.0 if along > 0.0 else -1.0)
            depth = max(d for d, _ in hit) - allow + 0.0005
            trial = Matrix.Translation(move.normalized() * depth) @ wpn
            if (trial.translation - start).length > max_move:
                break
            t_cost, t_hit, t_worst = overlap(trial)
            if t_cost >= cost:
                break
            wpn, cost, hit, worst = trial, t_cost, t_hit, t_worst
        return wpn, worst

    def overlap_sum(self, wpn, pts, allow):
        return sum(d - allow for d, _, _ in self.depths(wpn, pts) if d > allow)

    def search_axis(self, wpn, pts, axis, span=0.04, step=0.004, allow=0.004, prev=None, max_step=0.006):
        """1-D clearance search along a world axis: least overlap, then the move closest to the previous
        frame's (V85: an unconstrained pick jumped +4 -> -4 cm between frames)."""
        rows = []
        k = int(round(span / step))
        offsets = [i * step for i in range(-k, k + 1)]
        if prev is not None:
            offsets = [s for s in offsets if abs(s - prev) <= max_step + 1e-9] or [prev]
            offsets = sorted(set(offsets + [max(-span, min(span, prev))]))
        for s in offsets:
            m = Matrix.Translation(axis * s) @ wpn
            rows.append((self.overlap_sum(m, pts, allow), abs(s - (prev or 0.0)), s))
        best = min(r[0] for r in rows)
        s = min((r for r in rows if r[0] <= best + 0.002), key=lambda r: r[1])[2]
        return Matrix.Translation(axis * s) @ wpn, s

    def report(self, wpn, pts):
        rows = self.depths(wpn, pts)
        inside = [(d, z) for d, _, z in rows if d > 0.0]
        guard = [d for d, z in inside if z > HILT_Z[1]]
        hilt = [d for d, z in inside if z <= HILT_Z[1]]
        return {'hilt_max_mm': round(max(hilt + [0.0]) * 1000, 2), 'hilt_n_over_3mm': sum(d > 0.003 for d in hilt),
                'guard_max_mm': round(max(guard + [0.0]) * 1000, 2), 'guard_n': len(guard)}


def guard_hits(wpn, pts):
    inv = np.array(wpn.inverted())
    L = pts @ inv[:3, :3].T + inv[:3, 3]
    gx, gy, z0, z1 = GUARD
    hit = (np.abs(L[:, 0]) < gx) & (np.abs(L[:, 1]) < gy) & (L[:, 2] > z0) & (L[:, 2] < z1)
    return int(hit.sum())
