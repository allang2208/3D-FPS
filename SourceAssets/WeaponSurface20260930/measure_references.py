"""Area-weighted PBR measurement of the reference guns (plain CPython + numpy + PIL).

Inputs:  inspect/export/manifest.json, inspect/export/tex/*.png, inspect/geometry/<Key>.bin
Output:  inspect/reference_measurements.json (per material, per k-means cluster)

Samples are drawn uniformly by surface area on the runtime LOD0 source model. sRGB
base colour is linearised. M4's legacy Phong slots feed its PBR roughness map into a
Shininess input; those rows report the author's raw roughness map (authoring intent),
flagged `phong_slot`, because the runtime conversion is not a PBR reference.
"""
import json
import re
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

Image.MAX_IMAGE_PIXELS = None
O = Path(__file__).parent
EXP = O / 'inspect' / 'export'
GEOMETRY = O / 'inspect' / 'geometry'
manifest = json.loads((EXP / 'manifest.json').read_text(encoding='utf-8'))
_cache = {}


def srgb_to_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def load(name, mode):
    key = (name, mode)
    if key not in _cache:
        info = manifest['textures'][name]
        im = Image.open(EXP / 'tex' / info['export'])
        if mode == 'L':
            im = im.convert('RGB').split()[0]
        else:
            im = im.convert(mode)
        _cache[key] = im
    return _cache[key]


def sample(im, uv):
    """UE UV convention (V down): pixel row = v * height."""
    arr = np.asarray(im)
    h, w = arr.shape[:2]
    x = np.clip(((uv[:, 0] % 1.0) * w).astype(int), 0, w - 1)
    y = np.clip(((uv[:, 1] % 1.0) * h).astype(int), 0, h - 1)
    return arr[y, x].astype(np.float32) / 255.0


def highpass(im, uv, radius):
    if radius < 0.6:
        return None
    blurred = im.filter(ImageFilter.GaussianBlur(radius))
    return sample(im, uv) - sample(blurred, uv)


def role(name):
    n = name.lower()
    for key, words in [('normal', ['normal']), ('ao', ['_ao', 'occlusion', 'mixed_ao']),
                       ('metallic', ['metal']), ('roughness', ['rough', 'shininess']),
                       ('base', ['base', 'albedo', 'diffuse', 'color'])]:
        if any(w in n for w in words):
            return key
    return None


def read_geometry(path):
    with open(path, 'rb') as f:
        header = json.loads(f.readline().decode('utf-8'))
        V, T = header['vertices'], header['triangles']
        pos = np.fromfile(f, np.float32, V * 3).reshape(V, 3)
        tri = np.fromfile(f, np.int32, T * 3).reshape(T, 3)
        mat = np.fromfile(f, np.int32, T)
        uv = np.fromfile(f, np.float32, T * 6).reshape(T, 3, 2)
        nrm = np.fromfile(f, np.float32, T * 9).reshape(T, 3, 3)
    return header, pos, tri, mat, uv, nrm


def area_samples(pos, tri, uv, sel, count, rng):
    P = pos[tri[sel]].astype(np.float64)
    U = uv[sel].astype(np.float64)
    area = 0.5 * np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1)
    e1, e2 = U[:, 1] - U[:, 0], U[:, 2] - U[:, 0]
    uv_area = 0.5 * np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0])
    pick = rng.choice(len(area), size=count, p=area / area.sum())
    r1, r2 = rng.random(count), rng.random(count)
    s = np.sqrt(r1)
    w = np.stack([1 - s, s * (1 - r2), s * r2], 1)
    return (U[pick] * w[:, :, None]).sum(1), float(area.sum()), float(uv_area.sum()), int(len(area))


def kmeans(x, k, iters=30, seed=3):
    rng = np.random.default_rng(seed)
    c = x[rng.choice(len(x), k, replace=False)]
    for _ in range(iters):
        d = ((x[:, None, :] - c[None]) ** 2).sum(-1)
        lab = d.argmin(1)
        for j in range(k):
            if (lab == j).any():
                c[j] = x[lab == j].mean(0)
    return lab


def pct(v, qs=(10, 50, 90)):
    return [round(float(np.percentile(v, q)), 4) for q in qs]


def summarise(base, rough, metal, ao, nrm, micro, sel):
    lum = base[sel] @ np.array([0.2126, 0.7152, 0.0722])
    med = float(np.median(lum))
    wear = (lum > max(med * 2.2, med + 0.02)) & ((metal[sel] > 0.5) | (rough[sel] < np.median(rough[sel]) - 0.08))
    out = {
        'fraction': round(float(sel.mean()), 4),
        'base_linear_median': [round(float(np.median(base[sel, i])), 4) for i in range(3)],
        'luminance_p10_50_90': pct(lum),
        'roughness_p10_50_90': pct(rough[sel]),
        'metallic_mean': round(float(metal[sel].mean()), 3),
        'metallic_share_over_half': round(float((metal[sel] > 0.5).mean()), 3),
        'wear_share': round(float(wear.mean()), 4),
    }
    if wear.any():
        out['wear_base_linear_median'] = [round(float(np.median(base[sel][wear, i])), 4) for i in range(3)]
        out['wear_roughness_median'] = round(float(np.median(rough[sel][wear])), 3)
        out['wear_metallic_mean'] = round(float(metal[sel][wear].mean()), 3)
    if ao is not None:
        out['ao_p10_50'] = pct(ao[sel], (10, 50))
    if nrm is not None:
        slope = np.linalg.norm(nrm[sel], axis=1)
        out['normal_slope_p50_90_99'] = pct(slope, (50, 90, 99))
        out['normal_edge_share'] = round(float((slope > 0.3).mean()), 4)
    for key, v in micro.items():
        if v is not None:
            out[key] = round(float(np.std(v[sel])), 4)
    return out


def main():
  result = {}
  rng = np.random.default_rng(20260930)
  for geo in sorted(GEOMETRY.glob('*.bin')):
    key = geo.stem
    mesh = manifest['meshes'].get(key)
    if not mesh:
        continue
    header, pos, tri, mat, uv_all, _ = read_geometry(geo)
    # Materials may repeat across slots (AKM): measure each texture set once over all its slots.
    groups = {}
    for index, slot in enumerate(mesh['slots']):
        if slot['material'] and slot['textures']:
            name = slot['material'].split('.')[-1]
            groups.setdefault(name, {'textures': slot['textures'], 'slots': []})['slots'].append(index)
    report = {}
    for match, group in groups.items():
        sel = np.isin(mat, group['slots'])
        if not sel.any():
            continue
        textures = group['textures']
        uv, area, uv_area, tris = area_samples(pos, tri, uv_all, sel, int(min(300000, max(40000, sel.sum() * 3))), rng)
        roles = {}
        for param, tex in textures.items():
            r = role(tex) or role(param)
            if r and r not in roles:
                roles[r] = tex
        if 'base' not in roles:
            continue
        base_im = load(roles['base'], 'RGB')
        W = base_im.size[0]
        texel_per_cm = float(np.sqrt(uv_area / area) * W)
        base = srgb_to_linear(sample(base_im, uv))
        rough_im = load(roles['roughness'], 'L') if 'roughness' in roles else None
        rough_raw = sample(rough_im, uv) if rough_im else np.full(len(uv), 0.5, np.float32)
        metal = sample(load(roles['metallic'], 'L'), uv) if 'metallic' in roles else np.zeros(len(uv), np.float32)
        ao = sample(load(roles['ao'], 'L'), uv) if 'ao' in roles else None
        nrm = None
        if 'normal' in roles:
            n = sample(load(roles['normal'], 'RGB'), uv)
            nrm = n[:, :2] * 2 - 1
        phong = 'ShininessMap' in textures
        rough = rough_raw
        px_mm = texel_per_cm / 10.0
        micro = {}
        if rough_im:
            micro['roughness_detail_std_1mm'] = highpass(rough_im, uv, 1.0 * px_mm)
            micro['roughness_detail_std_5mm'] = highpass(rough_im, uv, 5.0 * px_mm)
        lum_im = base_im.convert('L')
        micro['luminance_detail_std_1mm'] = highpass(lum_im, uv, 1.0 * px_mm)
        feats = np.stack([np.log(base @ np.array([0.2126, 0.7152, 0.0722]) + 0.004), rough, metal,
                          (base[:, 0] - base[:, 2]) / (base.sum(1) + 0.01) * 2], 1)
        feats = (feats - feats.mean(0)) / (feats.std(0) + 1e-6)
        k = 3 if len(uv) > 30000 else 2
        lab = kmeans(feats[::4], k)
        centers = np.stack([feats[::4][lab == j].mean(0) for j in range(k)])
        lab_all = ((feats[:, None, :] - centers[None]) ** 2).sum(-1).argmin(1)
        entry = {'textures': roles, 'phong_slot': phong, 'slots': [mesh['slots'][i]['slot'] for i in group['slots']],
                 'triangles': int(tris), 'area_cm2': round(float(area), 1),
                 'texels_per_cm': round(texel_per_cm, 1), 'samples': int(len(uv)),
                 'all': summarise(base, rough, metal, ao, nrm, micro, np.ones(len(uv), bool)),
                 'clusters': [summarise(base, rough, metal, ao, nrm, micro, lab_all == j) for j in range(k)]}
        report[match] = entry
        print(key, match, 'texel/cm', entry['texels_per_cm'], 'base', entry['all']['base_linear_median'],
              'rough', entry['all']['roughness_p10_50_90'], 'metal', entry['all']['metallic_mean'], flush=True)
    result[key] = report
  (O / 'inspect' / 'reference_measurements.json').write_text(json.dumps(result, indent=1), encoding='utf-8')
  print('MEASURED', {k: len(v) for k, v in result.items()})


if __name__ == '__main__':
    main()
