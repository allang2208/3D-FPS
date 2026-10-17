"""Small FK / transform helpers for UE local bone rows [tx,ty,tz, qx,qy,qz,qw, sx,sy,sz] (cm)."""
import numpy as np


def q2m(q):
    x, y, z, w = q
    n = x * x + y * y + z * z + w * w
    s = 2.0 / n if n else 0.0
    return np.array([[1 - s * (y * y + z * z), s * (x * y - z * w), s * (x * z + y * w)],
                     [s * (x * y + z * w), 1 - s * (x * x + z * z), s * (y * z - x * w)],
                     [s * (x * z - y * w), s * (y * z + x * w), 1 - s * (x * x + y * y)]])


def m2q(m):
    t = np.trace(m)
    if t > 0:
        s = np.sqrt(t + 1.0) * 2; w = .25 * s
        x = (m[2, 1] - m[1, 2]) / s; y = (m[0, 2] - m[2, 0]) / s; z = (m[1, 0] - m[0, 1]) / s
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = np.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2; w = (m[2, 1] - m[1, 2]) / s
        x = .25 * s; y = (m[0, 1] + m[1, 0]) / s; z = (m[0, 2] + m[2, 0]) / s
    elif m[1, 1] > m[2, 2]:
        s = np.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2; w = (m[0, 2] - m[2, 0]) / s
        x = (m[0, 1] + m[1, 0]) / s; y = .25 * s; z = (m[1, 2] + m[2, 1]) / s
    else:
        s = np.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2; w = (m[1, 0] - m[0, 1]) / s
        x = (m[0, 2] + m[2, 0]) / s; y = (m[1, 2] + m[2, 1]) / s; z = .25 * s
    q = np.array([x, y, z, w]); return q / np.linalg.norm(q)


def row2m(r):
    m = np.eye(4); m[:3, :3] = q2m(r[3:7]) * np.asarray(r[7:10]); m[:3, 3] = r[:3]; return m


def m2row(m, scale=None):
    s = np.linalg.norm(m[:3, :3], axis=0) if scale is None else np.asarray(scale)
    r = m[:3, :3] / s
    return [*m[:3, 3].tolist(), *m2q(r).tolist(), *s.tolist()]


def inv(m):
    return np.linalg.inv(m)


def fk(names, parents, local_rows):
    """local_rows: {bone: row}. Returns {bone: 4x4 component transform}."""
    out = {}
    for n in names:
        p = parents.get(n)
        m = row2m(local_rows[n])
        out[n] = out[p] @ m if p in out else m
    return out


def local_from_world(names, parents, world):
    out = {}
    for n in names:
        p = parents.get(n)
        out[n] = inv(world[p]) @ world[n] if p in world else world[n]
    return out


def slerp(a, b, t):
    a = np.asarray(a, float); b = np.asarray(b, float)
    d = float(np.dot(a, b))
    if d < 0: b = -b; d = -d
    if d > .9995:
        q = a + t * (b - a); return q / np.linalg.norm(q)
    th = np.arccos(d); s = np.sin(th)
    return (np.sin((1 - t) * th) * a + np.sin(t * th) * b) / s


def blend_m(a, b, t):
    """Blend two rigid 4x4 transforms (translation lerp, rotation slerp)."""
    qa, qb = m2q(a[:3, :3] / np.linalg.norm(a[:3, :3], axis=0)), m2q(b[:3, :3] / np.linalg.norm(b[:3, :3], axis=0))
    sa, sb = np.linalg.norm(a[:3, :3], axis=0), np.linalg.norm(b[:3, :3], axis=0)
    m = np.eye(4); m[:3, :3] = q2m(slerp(qa, qb, t)) * (sa + (sb - sa) * t); m[:3, 3] = a[:3, 3] + (b[:3, 3] - a[:3, 3]) * t
    return m


def smooth(t):
    t = min(1.0, max(0.0, t)); return t * t * (3 - 2 * t)


def window(f, a, b):
    """0 before a, smooth rise to 1 at b."""
    return smooth((f - a) / max(b - a, 1e-6))
