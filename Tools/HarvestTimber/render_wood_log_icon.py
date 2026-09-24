"""Paint the wood inventory icon from the exported short-log mesh and its bark texture.

Orthographic side view. The log stands on the long axis of a 1x2 canvas.
The silhouette centre is the frame centre, and the long side fills 91 percent,
matching ColdSteelWeaponIcons.
"""
from pathlib import Path
import numpy as np
from PIL import Image

OBJ = Path(r"D:\FPS3D\FPSGAME\Saved\HarvestTimber\SM_PoplarLog_Solid_A.obj")
TEX = Path(r"D:\FPS3D\FPSGAME\SourceAssets\HarvestTimber20260913\SolidRepair\Delivery\T_PoplarSolid_BaseColor.png")
OUT = Path(r"D:\FPS3D\FPSGAME\Content\ColdSteelData\Icons\wood_log.png")
WIDTH, HEIGHT = 512, 1024
FILL = 0.91

verts, uvs, faces = [], [], []
for line in OBJ.read_text(encoding="utf-8", errors="replace").splitlines():
    if line.startswith("v "):
        _, x, y, z = line.split()
        verts.append((float(x), float(y), float(z)))
    elif line.startswith("vt "):
        parts = line.split()
        uvs.append((float(parts[1]), float(parts[2])))
    elif line.startswith("f "):
        tri = []
        for corner in line.split()[1:4]:
            v, vt = corner.split("/")[:2]
            tri.append((int(v) - 1, int(vt) - 1))
        faces.append(tri)

points = np.asarray(verts, np.float64)
uv = np.asarray(uvs, np.float64)
center = (points.min(0) + points.max(0)) * 0.5
local = points - center
extent = points.max(0) - points.min(0)
up = int(np.argmax(extent))
view = int(np.argmin(extent))
right = ({0, 1, 2} - {up, view}).pop()
# Image X follows `right`, image Y follows `up` (top is +up).
proj = np.stack([local[:, right], local[:, up]], axis=1)
span = proj.max(0) - proj.min(0)
mid = (proj.max(0) + proj.min(0)) * 0.5
scale = FILL * min(WIDTH / span[0], HEIGHT / span[1])
screen = np.empty_like(proj)
screen[:, 0] = (proj[:, 0] - mid[0]) * scale + WIDTH * 0.5
screen[:, 1] = HEIGHT * 0.5 - (proj[:, 1] - mid[1]) * scale

texture = np.asarray(Image.open(TEX).convert("RGB"), np.float32)
th, tw = texture.shape[:2]
canvas = np.zeros((HEIGHT, WIDTH, 3), np.float32)
depth = np.full((HEIGHT, WIDTH), np.inf, np.float32)
light = np.array([0.35, 0.25, 0.90], np.float32)
light /= np.linalg.norm(light)

def shade(normal):
    n = normal / (np.linalg.norm(normal) + 1e-8)
    lambert = 0.72 + 0.85 * max(0.0, float(np.dot(n, light)))
    return lambert

for (ia, ib, ic) in faces:
    p = screen[[ia[0], ib[0], ic[0]]]
    q = uv[[ia[1], ib[1], ic[1]]]
    z = local[[ia[0], ib[0], ic[0]], view]
    minx = max(int(np.floor(p[:, 0].min())), 0)
    maxx = min(int(np.ceil(p[:, 0].max())), WIDTH - 1)
    miny = max(int(np.floor(p[:, 1].min())), 0)
    maxy = min(int(np.ceil(p[:, 1].max())), HEIGHT - 1)
    if minx > maxx or miny > maxy:
        continue
    area = (p[1, 0] - p[0, 0]) * (p[2, 1] - p[0, 1]) - (p[2, 0] - p[0, 0]) * (p[1, 1] - p[0, 1])
    if abs(area) < 1e-8:
        continue
    xs = np.arange(minx, maxx + 1) + 0.5
    ys = np.arange(miny, maxy + 1) + 0.5
    gx, gy = np.meshgrid(xs, ys)
    w0 = ((p[1, 0] - gx) * (p[2, 1] - gy) - (p[2, 0] - gx) * (p[1, 1] - gy)) / area
    w1 = ((p[2, 0] - gx) * (p[0, 1] - gy) - (p[0, 0] - gx) * (p[2, 1] - gy)) / area
    w2 = 1.0 - w0 - w1
    mask = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
    if not np.any(mask):
        continue
    zz = w0 * z[0] + w1 * z[1] + w2 * z[2]
    nearer = mask & (zz < depth[miny:maxy + 1, minx:maxx + 1])
    if not np.any(nearer):
        continue
    uu = np.clip(w0 * q[0, 0] + w1 * q[1, 0] + w2 * q[2, 0], 0, 0.999)
    vv = np.clip(w0 * q[0, 1] + w1 * q[1, 1] + w2 * q[2, 1], 0, 0.999)
    tx = (uu[nearer] * (tw - 1)).astype(np.int32)
    ty = ((1.0 - vv[nearer]) * (th - 1)).astype(np.int32)
    color = texture[ty, tx] * shade(np.cross(points[ib[0]] - points[ia[0]], points[ic[0]] - points[ia[0]]))
    block_d = depth[miny:maxy + 1, minx:maxx + 1]
    block_c = canvas[miny:maxy + 1, minx:maxx + 1]
    block_d[nearer] = zz[nearer]
    block_c[nearer] = np.clip(color, 0, 255)
    depth[miny:maxy + 1, minx:maxx + 1] = block_d
    canvas[miny:maxy + 1, minx:maxx + 1] = block_c

rgb = canvas.astype(np.uint8)
alpha = np.where(np.isfinite(depth), 255, 0).astype(np.uint8)
image = Image.fromarray(np.dstack([rgb, alpha]), "RGBA")
image.save(OUT)
ys, xs = np.where(alpha > 0)
print("saved", OUT, "pixels", int(alpha.sum() // 255), "span", int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1))
