"""Per-slot statistics of the baked A762 masks (plain CPython), area-weighted on UV1/UV0."""
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
import measure_references as M  # noqa: E402

rng = np.random.default_rng(11)


def stats(key, mask_name, uv_override=None):
    header, pos, tri, mat, uv0, _ = M.read_geometry(M.GEOMETRY / (key + '.bin'))
    uv = uv0 if uv_override is None else uv_override
    im = np.asarray(Image.open(HERE / 'Bake' / mask_name)).astype(np.float32) / 255
    h, w = im.shape[:2]
    out = {}
    for i, name in enumerate(header['slots']):
        sel = mat == i
        m = header['materials'][i] or ''
        if not sel.any() or any(k in m for k in ('Manny', 'BarePalm', 'BareNative')):
            continue
        s, *_ = M.area_samples(pos, tri, uv, sel, 20000, rng)
        x = np.clip((s[:, 0] % 1 * w).astype(int), 0, w - 1)
        y = np.clip((s[:, 1] % 1 * h).astype(int), 0, h - 1)
        px = im[y, x]
        out[name] = {'edge_mean': round(float(px[:, 0].mean()), 3), 'edge_share_gt_half': round(float((px[:, 0] > .5).mean()), 3),
                     'cavity_mean': round(float(px[:, 1].mean()), 3),
                     'ao_p10_50_90': [round(float(v), 3) for v in np.percentile(px[:, 2], [10, 50, 90])],
                     'ao_below_0.15': round(float((px[:, 2] < .15).mean()), 3)}
        print(key, name.ljust(32), out[name], flush=True)
    return out


with open(HERE / 'Bake' / 'A762_uv1.bin', 'rb') as f:
    hdr = json.loads(f.readline())
    uv1 = np.fromfile(f, np.float32, hdr['triangles'] * 6).reshape(-1, 3, 2)
report = {'A762': stats('A762', 'T_A762_WS_Mask.png', uv1),
          'A762_RearSight': stats('A762_RearSight', 'T_A762_RearSight_WS_Mask.png'),
          'A762_FrontSight': stats('A762_FrontSight', 'T_A762_FrontSight_WS_Mask.png')}
(HERE / 'Bake' / 'mask_stats.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
