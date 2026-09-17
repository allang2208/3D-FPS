"""Offline render of the dumped pavilion meshes (numpy z-buffer, flat Lambert).

No Unreal involved: reads the triangle-soup OBJ dumps in preview_20260917/ and writes PNGs
so the geometry can be eyeballed without opening the editor.
"""

import math
import os

import numpy as np
from PIL import Image

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preview_20260917")
MARBLE = np.array([0.87, 0.855, 0.82])
SKY_TOP = np.array([0.40, 0.56, 0.77])
SKY_BOT = np.array([0.74, 0.79, 0.84])
LIGHT = np.array([-0.45, -0.55, 0.70])
LIGHT = LIGHT / np.linalg.norm(LIGHT)


def load(name):
    verts = []
    for line in open(os.path.join(DIR, name + ".obj")):
        t = line.split()
        if t and t[0] == "v":
            verts.append((float(t[1]), float(t[2]), float(t[3])))
    return np.array(verts, dtype=float).reshape(-1, 3, 3)


def at(tris, x=0.0, y=0.0, z=0.0):
    return tris + np.array([x, y, z], dtype=float)


def column_ring(base, radius, count, z, phase=0.0):
    out = []
    for k in range(count):
        a = 2.0 * math.pi * k / count + math.radians(phase)
        out.append(at(base, radius * math.cos(a), radius * math.sin(a), z))
    return out


def render(tris_list, cam, target, width=760, height=560, fov=46.0, ambient=0.30):
    tris = np.concatenate(tris_list, axis=0)
    cam = np.array(cam, dtype=float)
    fwd = np.array(target, dtype=float) - cam
    fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, np.array([0.0, 0.0, 1.0]))
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)

    centroid = tris.mean(axis=1)
    normal = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    area = np.linalg.norm(normal, axis=1)
    good = area > 1e-9
    normal = normal[good] / area[good][:, None]
    tris = tris[good]
    centroid = centroid[good]

    view = cam - centroid                     # back-face cull
    face_view = np.clip((normal * view).sum(axis=1) /
                        (np.linalg.norm(view, axis=1) + 1e-9), -1.0, 1.0)
    keep = face_view > -0.05
    tris, normal = tris[keep], normal[keep]
    print("    faces rendered: %d" % len(tris))

    rel = tris - cam                      # (F, 3 vertices, 3 axes)
    cx = (rel * right).sum(axis=-1)
    cy = (rel * up).sum(axis=-1)
    cz = (rel * fwd).sum(axis=-1)
    z_face = cz.mean(axis=1)              # flat depth per face for the z test
    f = (width * 0.5) / math.tan(math.radians(fov) * 0.5)
    sx = cx * f / np.maximum(cz, 1e-6) + width * 0.5
    sy = height * 0.5 - cy * f / np.maximum(cz, 1e-6)

    grad = np.linspace(0.0, 1.0, height)[:, None, None]
    image = SKY_TOP * (1 - grad) + SKY_BOT * grad
    image = np.repeat(image, width, axis=1)
    zbuf = np.full((height, width), np.inf)

    shade = ambient + (1.0 - ambient) * np.clip(normal @ LIGHT, 0.0, 1.0)
    color = np.clip(MARBLE[None, :] * shade[:, None], 0.0, 1.0)

    for i in np.argsort(-z_face):
        z = z_face[i]
        if z < 15.0:
            continue
        xs, ys = sx[i], sy[i]
        x0 = int(max(0, math.floor(xs.min())))
        x1 = int(min(width - 1, math.ceil(xs.max())))
        y0 = int(max(0, math.floor(ys.min())))
        y1 = int(min(height - 1, math.ceil(ys.max())))
        if x1 < x0 or y1 < y0:
            continue
        denom = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
        if abs(denom) < 1e-9:
            continue
        px = np.arange(x0, x1 + 1) + 0.5
        py = np.arange(y0, y1 + 1) + 0.5
        PX, PY = np.meshgrid(px, py)
        w0 = ((ys[1] - ys[2]) * (PX - xs[2]) + (xs[2] - xs[1]) * (PY - ys[2])) / denom
        w1 = ((ys[2] - ys[0]) * (PX - xs[2]) + (xs[0] - xs[2]) * (PY - ys[2])) / denom
        w2 = 1.0 - w0 - w1
        mask = (w0 > -0.003) & (w1 > -0.003) & (w2 > -0.003)
        if not mask.any():
            continue
        sub = zbuf[y0:y1 + 1, x0:x1 + 1]
        closer = mask & (z < sub)
        if not closer.any():
            continue
        sub[closer] = z
        image[y0:y1 + 1, x0:x1 + 1][closer] = color[i]
    return (np.clip(image, 0.0, 1.0) * 255).astype(np.uint8)


def save(name, array):
    Image.fromarray(array).save(os.path.join(DIR, name))
    print("    wrote %s" % name)


def report(label, tris_list):
    total = sum(len(t) for t in tris_list)
    stack = np.concatenate(tris_list, axis=0)
    lo, hi = stack.reshape(-1, 3).min(axis=0), stack.reshape(-1, 3).max(axis=0)
    print("  %s: %d faces, bbox %.0f x %.0f x %.0f, z %.0f..%.0f" % (
        label, total, hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2], lo[2], hi[2]))


print("== loading ==")
base = load("p2_base")
arch = load("p2_arch")
dome = load("p2_dome")
column = load("p2_column")
old_style = load("stylobate")
old_ring = load("ring")
old_dome = load("p2_old_dome")
print("  column mesh: %d faces" % len(column))

NEW = column_ring(column, 360.0, 10, 20.0) + [base, at(arch, 0, 0, 280.0), at(dome, 0, 0, 360.0)]
OLD = column_ring(column, 240.0, 8, 20.0) + [old_style, at(old_ring, 0, 0, 280.0), at(old_dome, 0, 0, 320.0)]
report("new pavilion", NEW)
report("old pavilion", OLD)

print("== 1. before / after ==")
pair = [at(t, -1050, 0, 0) for t in OLD] + [at(t, 1250, 0, 0) for t in NEW]
save("p2_vs_old.png", render(pair, (100.0, -4600.0, 1250.0), (100.0, 0.0, 330.0), 900, 520, 40.0))

print("== 2. exterior, eye level ==")
save("p2_exterior.png", render(NEW, (1500.0, -1500.0, 260.0), (0.0, 0.0, 340.0), 860, 640, 46.0))
save("p2_front.png", render(NEW, (0.0, -2400.0, 330.0), (0.0, 0.0, 330.0), 860, 640, 40.0))

print("== 3. interior, looking up at the soffit ==")
save("p2_interior.png", render(NEW, (0.0, -120.0, 175.0), (30.0, 140.0, 760.0), 800, 620, 92.0))

print("== 4. dome only, eye level ==")
print("== 4b. player view (eye 1.7 m, 16 m away) ==")
save("p2_player.png", render(NEW, (700.0, -1480.0, 170.0), (0.0, 0.0, 420.0), 860, 620, 46.0))
save("p2_player_close.png", render(NEW, (500.0, -900.0, 170.0), (0.0, 0.0, 500.0), 860, 620, 60.0))

save("p2_dome.png", render([at(dome, 0, 0, 0)], (900.0, -1000.0, 180.0), (0.0, 0.0, 200.0), 800, 620, 46.0))

print("== 5. dome soffit from below (detail) ==")
save("p2_soffit.png", render([at(dome, 0, 0, 0)], (0.0, -40.0, -140.0), (0.0, 40.0, 250.0), 800, 620, 95.0))
