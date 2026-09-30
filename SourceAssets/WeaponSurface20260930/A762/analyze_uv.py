"""A762 UV0 layout per slot: bounds, density, overlap -> bake grouping (plain CPython).

Writes A762/uv_layout.json. Overlap is the ratio of summed triangle UV area to the
rasterised union at 1024 px; values near 1 mean the slot can own a mask texture.
"""
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
import measure_references as M  # noqa: E402

R = 1024
out = {}
for key in ['A762', 'A762_RearSight', 'A762_FrontSight']:
    header, pos, tri, mat, uv, _ = M.read_geometry(M.GEOMETRY / (key + '.bin'))
    P = pos[tri].astype(np.float64)
    area = 0.5 * np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1)
    U = uv.astype(np.float64)
    e1, e2 = U[:, 1] - U[:, 0], U[:, 2] - U[:, 0]
    uv_area = 0.5 * np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0])
    slots = {}
    for index, name in enumerate(header['slots']):
        sel = mat == index
        if not sel.any():
            continue
        u = U[sel]
        lo, hi = u.reshape(-1, 2).min(0), u.reshape(-1, 2).max(0)
        im = Image.new('L', (R, R), 0)
        draw = ImageDraw.Draw(im)
        frac = u % 1.0
        for t in frac:
            draw.polygon([(t[0][0] * R, t[0][1] * R), (t[1][0] * R, t[1][1] * R), (t[2][0] * R, t[2][1] * R)], fill=255)
        union = (np.asarray(im) > 0).mean()
        density = float(np.sqrt(uv_area[sel].sum() / max(area[sel].sum(), 1e-9)))
        slots[name] = {
            'index': index, 'material': header['materials'][index], 'triangles': int(sel.sum()),
            'area_cm2': round(float(area[sel].sum()), 2), 'uv_area': round(float(uv_area[sel].sum()), 5),
            'uv_bounds': [round(float(x), 4) for x in (*lo, *hi)], 'uv_union': round(float(union), 5),
            'overlap_ratio': round(float(uv_area[sel].sum() / max(union, 1e-9)), 3),
            'uv_per_cm': round(density, 5),
            'bbox_cm': [round(float(x), 2) for x in (*P[sel].reshape(-1, 3).min(0), *P[sel].reshape(-1, 3).max(0))],
        }
        print(key, name.ljust(32), 'tris', slots[name]['triangles'], 'area', slots[name]['area_cm2'],
              'uv', slots[name]['uv_bounds'], 'union', slots[name]['uv_union'], 'overlap', slots[name]['overlap_ratio'],
              'uv/cm', slots[name]['uv_per_cm'], flush=True)
    out[key] = {'path': header['path'], 'slots': slots,
                'bbox_cm': [round(float(x), 2) for x in (*pos.min(0), *pos.max(0))]}
(HERE / 'uv_layout.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
