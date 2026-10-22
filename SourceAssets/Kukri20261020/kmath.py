"""Small UE-convention transform helpers for offline kukri authoring (no Blender/UE needed).

Transforms are (p, q, s): p translation (cm or bone units), q quaternion (w, x, y, z), s scale vector.
Composition follows FTransform: world = local * parent  ->  compose(local, parent).
Mesh component space of the sword viewmodel: forward = -Y, right = +X, up = +Z
(the viewmodel is attached to the camera with yaw +90).
"""
import json
import math
from pathlib import Path

import numpy as np

P = Path(__file__).resolve().parent


def qnorm(q):
    q = np.asarray(q, float)
    return q / np.linalg.norm(q)


def qmul(a, b):
    """Hamilton product a*b (apply b first, then a) in (w,x,y,z)."""
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return np.array([w1*w2 - x1*x2 - y1*y2 - z1*z2,
                     w1*x2 + x1*w2 + y1*z2 - z1*y2,
                     w1*y2 - x1*z2 + y1*w2 + z1*x2,
                     w1*z2 + x1*y2 - y1*x2 + z1*w2])


def qconj(q):
    return np.array([q[0], -q[1], -q[2], -q[3]])


def qrot(q, v):
    v = np.asarray(v, float)
    u = np.array(q[1:])
    w = q[0]
    return 2*np.dot(u, v)*u + (w*w - np.dot(u, u))*v + 2*w*np.cross(u, v)


def qaxis(axis, angle):
    axis = np.asarray(axis, float)
    axis = axis/np.linalg.norm(axis)
    h = angle*.5
    return np.array([math.cos(h), *(axis*math.sin(h))])


def qbetween(a, b):
    a = np.asarray(a, float)/np.linalg.norm(a)
    b = np.asarray(b, float)/np.linalg.norm(b)
    d = np.dot(a, b)
    if d < -0.999999:
        ortho = np.cross([1, 0, 0], a)
        if np.linalg.norm(ortho) < 1e-6:
            ortho = np.cross([0, 1, 0], a)
        return qaxis(ortho, math.pi)
    c = np.cross(a, b)
    return qnorm(np.array([1+d, *c]))


def qslerp(a, b, t):
    a = qnorm(a); b = qnorm(b)
    d = np.dot(a, b)
    if d < 0:
        b = -b; d = -d
    if d > 0.9995:
        return qnorm(a + (b-a)*t)
    th = math.acos(d)
    return (a*math.sin((1-t)*th) + b*math.sin(t*th))/math.sin(th)


def qmat(q):
    w, x, y, z = q
    return np.array([[1-2*(y*y+z*z), 2*(x*y-w*z), 2*(x*z+w*y)],
                     [2*(x*y+w*z), 1-2*(x*x+z*z), 2*(y*z-w*x)],
                     [2*(x*z-w*y), 2*(y*z+w*x), 1-2*(x*x+y*y)]])


def qfrommat(m):
    m = np.asarray(m, float)
    t = m[0, 0]+m[1, 1]+m[2, 2]
    if t > 0:
        s = math.sqrt(t+1)*2
        q = [.25*s, (m[2, 1]-m[1, 2])/s, (m[0, 2]-m[2, 0])/s, (m[1, 0]-m[0, 1])/s]
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = math.sqrt(1+m[0, 0]-m[1, 1]-m[2, 2])*2
        q = [(m[2, 1]-m[1, 2])/s, .25*s, (m[0, 1]+m[1, 0])/s, (m[0, 2]+m[2, 0])/s]
    elif m[1, 1] > m[2, 2]:
        s = math.sqrt(1+m[1, 1]-m[0, 0]-m[2, 2])*2
        q = [(m[0, 2]-m[2, 0])/s, (m[0, 1]+m[1, 0])/s, .25*s, (m[1, 2]+m[2, 1])/s]
    else:
        s = math.sqrt(1+m[2, 2]-m[0, 0]-m[1, 1])*2
        q = [(m[1, 0]-m[0, 1])/s, (m[0, 2]+m[2, 0])/s, (m[1, 2]+m[2, 1])/s, .25*s]
    return qnorm(q)


def qfromxz(x, z):
    """Rotation whose local X maps to x and local Z is as close as possible to z (FRotationMatrix::MakeFromXZ)."""
    x = np.asarray(x, float); x = x/np.linalg.norm(x)
    y = np.cross(z, x); y = y/np.linalg.norm(y)
    z2 = np.cross(x, y)
    return qfrommat(np.column_stack([x, y, z2]))


def qfromzx(z, x):
    z = np.asarray(z, float); z = z/np.linalg.norm(z)
    y = np.cross(z, x); y = y/np.linalg.norm(y)
    x2 = np.cross(y, z)
    return qfrommat(np.column_stack([x2, y, z]))


class T:
    __slots__ = ('p', 'q', 's')

    def __init__(self, p=(0, 0, 0), q=(1, 0, 0, 0), s=(1, 1, 1)):
        self.p = np.asarray(p, float)
        self.q = qnorm(q)
        self.s = np.asarray(s, float)

    @staticmethod
    def packed(v):
        return T(v[0:3], v[3:7], v[7:10])

    def pack(self):
        return [*map(float, self.p), *map(float, self.q), *map(float, self.s)]

    def copy(self):
        return T(self.p.copy(), self.q.copy(), self.s.copy())

    def __mul__(self, parent):
        """self (local) * parent  -> world (FTransform order)."""
        return T(qrot(parent.q, parent.s*self.p) + parent.p, qmul(parent.q, self.q), parent.s*self.s)

    def inverse(self):
        iq = qconj(self.q)
        inv_s = 1.0/self.s
        return T(inv_s*qrot(iq, -self.p), iq, inv_s)

    def relative_to(self, other):
        """self expressed in other's space: self * other^-1 (uniform scale assumed)."""
        return self*other.inverse()

    def point(self, v):
        return qrot(self.q, self.s*np.asarray(v, float)) + self.p

    def vector(self, v):
        return qrot(self.q, np.asarray(v, float))

    def axis(self, i):
        e = np.zeros(3); e[i] = 1
        return qrot(self.q, e)


def lerp_t(a, b, t):
    return T(a.p+(b.p-a.p)*t, qslerp(a.q, b.q, t), a.s+(b.s-a.s)*t)


class Rig:
    def __init__(self, dump):
        self.names = dump['names']
        self.parents = dump['parents']
        self.index = {n: i for i, n in enumerate(self.names)}
        self.ref_local = {n: T.packed(dump['ref_local'][n]) for n in self.names}

    def world(self, local):
        out = {}
        for n, par in zip(self.names, self.parents):
            out[n] = local[n].copy() if par is None else local[n]*out[par]
        return out

    def localize(self, world):
        out = {}
        for n, par in zip(self.names, self.parents):
            out[n] = world[n].copy() if par is None else world[n].relative_to(world[par])
        return out

    def descendants(self, name):
        res = {name}
        changed = True
        while changed:
            changed = False
            for n, par in zip(self.names, self.parents):
                if par in res and n not in res:
                    res.add(n); changed = True
        return res


def load_dump():
    return json.loads((P/'Work'/'ue_sword_dump.json').read_text('utf-8'))


def frame_local(rig, clip, k):
    fr = clip['frames'][k]
    return {n: T.packed(fr[i]) for i, n in enumerate(rig.names)}


# Mesh component space <-> camera space (camera: +X forward, +Y right, +Z up).
def mesh_to_cam(v):
    v = np.asarray(v, float)
    return np.array([-v[1], v[0], v[2]])


def cam_to_mesh(v):
    v = np.asarray(v, float)
    return np.array([v[1], -v[0], v[2]])


def ndc(cam, hfov_deg=90.0, aspect=16/9):
    """Project a camera-space point with UE's horizontal FOV. Returns (x right, y down) in [-1,1]."""
    x, y, z = cam
    if x <= 1e-3:
        return (float('nan'), float('nan'))
    t = math.tan(math.radians(hfov_deg)/2)
    return (y/(x*t), -z/(x*t/aspect))
