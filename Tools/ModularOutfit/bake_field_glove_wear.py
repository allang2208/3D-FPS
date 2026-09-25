"""Bake knuckle/webbing wear on the shared M4 field-glove UV and stamp a safe island."""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

PROJECT = Path("D:/FPS3D/FPSGAME")
GLOVE = json.loads((PROJECT / "SourceAssets/ModularOutfit20260925/FittedFieldGlovesV1/Authored/M4.json").read_text())
ANATOMY = json.loads((PROJECT / "SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json").read_text())["anatomy"]
OUT = PROJECT / "SourceAssets/ModularOutfit20260925/FieldGlovesLeatherV1"
SIZE = 4096
SAFE = (0.004, 0.004)

KNUCKLE = {
    "thumb_01_l", "thumb_01_r",
    "index_01_l", "index_01_r", "index_02_l", "index_02_r",
    "middle_01_l", "middle_01_r", "middle_02_l", "middle_02_r",
    "ring_01_l", "ring_01_r", "ring_02_l", "ring_02_r",
    "pinky_01_l", "pinky_01_r", "pinky_02_l", "pinky_02_r",
}


def unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def smooth(a, b, v):
    t = np.clip((v - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def vertex_normals(p, t):
    corners = p[t]
    face = -unit(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]))
    result = np.zeros_like(p)
    for k in range(3):
        a = unit(corners[:, (k + 1) % 3] - corners[:, k])
        b = unit(corners[:, (k + 2) % 3] - corners[:, k])
        angle = np.arccos(np.clip((a * b).sum(1), -1, 1))
        np.add.at(result, t[:, k], face * angle[:, None])
    return unit(result)


p = np.asarray(GLOVE["positions"], dtype=np.float64) * 0.01
t = np.asarray(GLOVE["triangles"], dtype=np.int32)
uv = np.asarray(GLOVE["uv"], dtype=np.float64)
weights = GLOVE["weights"]
n = vertex_normals(p, t)
dorsal = np.zeros_like(p)
for side, frame in ANATOMY.items():
    belongs = p[:, 0] < 0 if side == "l" else p[:, 0] > 0
    digit_dorsal = {d["bone"]: np.asarray(d["dorsal"], dtype=np.float64) for d in frame["digits"]}
    for vi in np.flatnonzero(belongs):
        w = weights[vi]
        total = sum(value for name, value in w.items() if name in digit_dorsal)
        dorsal[vi] = np.asarray(frame["dorsal"], dtype=np.float64) * max(0, 1 - total)
        for name, value in w.items():
            if name in digit_dorsal:
                dorsal[vi] += digit_dorsal[name] * value
dorsal = unit(dorsal)
back = smooth(-0.15, 0.65, (n * dorsal).sum(1))
wear = np.zeros(len(p))
for vi, w in enumerate(weights):
    knuckle = sum(value for name, value in w.items() if name in KNUCKLE)
    thumb = w.get("thumb_01_l", 0.0) + w.get("thumb_01_r", 0.0)
    index = w.get("index_01_l", 0.0) + w.get("index_01_r", 0.0)
    web = min(1.0, 6.0 * thumb * index)
    wear[vi] = min(1.0, knuckle * 1.35 * back[vi] + web)
face_wear = wear[t].mean(1)


def pixel(uv_xy, size):
    return (uv_xy[0] * (size - 1), (1 - uv_xy[1]) * (size - 1))


mask = Image.new("L", (SIZE, SIZE), 0)
draw = ImageDraw.Draw(mask)
for fi, face_uv in enumerate(uv):
    value = int(round(255 * float(face_wear[fi])))
    if value <= 0:
        continue
    draw.polygon([pixel(pt, SIZE) for pt in face_uv], fill=value)
mask = mask.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(1.1))
mask.save(OUT / "T_FieldGloves_Wear.png")


def stamp_safe(path, kind):
    im = Image.open(path)
    arr = np.array(im)
    size = arr.shape[0]
    x, y = [int(round(c * (size - 1))) for c in (SAFE[0], 1 - SAFE[1])]
    pad = max(6, size // 128)
    y0, y1 = max(0, y - pad), min(size, y + pad + 1)
    x0, x1 = max(0, x - pad), min(size, x + pad + 1)
    if kind == "regions":
        arr[y0:y1, x0:x1] = (255, 0, 0)
    elif kind == "wear":
        arr[y0:y1, x0:x1] = 0
    elif kind == "cuff":
        arr[y0:y1, x0:x1] = 255
    elif kind == "normal":
        arr[y0:y1, x0:x1] = (128, 128, 255)
    Image.fromarray(arr).save(path)


stamp_safe(OUT / "T_FieldGloves_Wear.png", "wear")
stamp_safe(OUT / "T_FieldGloves_LeatherRegions.png", "regions")
stamp_safe(OUT / "T_FieldGloves_StitchNormal.png", "normal")
stamp_safe(OUT / "T_FieldGloves_CuffField.png", "cuff")
stamp_safe(OUT / "T_FieldGloves_CuffRollNormal.png", "normal")
metrics = {
    "source": str(PROJECT / "SourceAssets/ModularOutfit20260925/FittedFieldGlovesV1/Authored/M4.json"),
    "wear_faces": int((face_wear > 0.05).sum()),
    "wear_mean": float(face_wear.mean()),
    "safe_uv": list(SAFE),
    "runtime_tested": False,
}
(OUT / "wear_report.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
print(json.dumps(metrics), flush=True)
