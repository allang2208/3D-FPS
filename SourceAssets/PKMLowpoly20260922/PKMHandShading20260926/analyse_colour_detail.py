"""PKMHandShading20260926 - quantify the ONE skin-fixed colour channel Sprint47 never touched.

Sprint47 isotropised only the SkinMicro height/normal texture (user: no change, rolled back).
The arm material multiplies base colour by  tone = 2 * T_M4OriginalShape_SkinColourDetail
(sampled triplanar in rest space, 8 cm tile, strength 0.55 -> per-channel albedo factor
0.45 + 1.1*tex, i.e. up to -19%/+19%).  That texture is baked from the SAME CC0 scan
(Skin_Human_002_COLOR.png) whose DISP map measured 2.23x directional @62.5 deg.
This script measures whether the colour detail carries the same directional comb and how
much albedo contrast it can put on the forearm, using the Sprint47 method verbatim.

Read-only.  No UE, no builds.  Output: colour_detail_report.json + factor preview PNG.
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

BASE = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ModularOutfit20260924\OriginalShapeBareM4')
LIVE = BASE / 'WristContourV4'           # the variant referenced by the live materials
SCAN = BASE / 'RefinedSkinV3' / 'External' / 'SkinHuman002'
OUT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922\PKMHandShading20260926')
TILE_CM = 8.0                            # bake_refined_skin_m4.py:9
STRENGTH = 0.55                          # ColourDetailStrength scalar default

R = {}


def angular_energy(f, label):
    """Sprint47 analyse_grain.anisotropy, verbatim method, returns dict + radial peak."""
    f = f - f.mean()
    win = np.hanning(f.shape[0])[:, None] * np.hanning(f.shape[1])[None, :]
    F = np.fft.fftshift(np.abs(np.fft.fft2(f * win)) ** 2)
    n0, n1 = f.shape
    cy, cx = n0 // 2, n1 // 2
    y, x = np.mgrid[0:n0, 0:n1]
    r = np.hypot(y - cy, x - cx)
    th = np.arctan2(y - cy, x - cx) % np.pi
    m = (r > n0 * 0.02) & (r < n0 * 0.45)
    e, t = F[m], th[m]
    bins = np.linspace(0, np.pi, 37)
    idx = np.clip(np.digitize(t, bins) - 1, 0, 35)
    ang = np.bincount(idx, weights=e, minlength=36)
    ang /= max(ang.sum(), 1e-30)
    peak = ang.max() * 36.0
    best = int(np.argmax(ang))
    deg = float(np.degrees(0.5 * (bins[best] + bins[best + 1])))
    entropy = float(-(ang * np.log(ang + 1e-12)).sum() / np.log(36))
    # dominant radial band (cycles per texture) -> feature size on skin
    rb = np.bincount(np.clip(r[m].astype(int), 0, n0 // 2 - 1), weights=e,
                     minlength=n0 // 2)
    k = int(np.argmax(rb[2:]) + 2)
    texel_mm = TILE_CM * 10.0 / 2048.0
    band_mm = float((2048.0 / k) * texel_mm) if k else float('inf')
    print('  %-24s peak/iso %5.2fx @ %5.1f deg  entropy %.3f  dominant band ~%.1f mm'
          % (label, peak, deg, entropy, band_mm))
    return {'peak_over_iso': peak, 'peak_angle_deg': deg, 'spectral_entropy': entropy,
            'dominant_radial_cycles': k, 'dominant_band_mm_on_skin': band_mm}


print('=== live ColourDetail texture (WristContourV4, sampled by M_BareNative_Default / M_BareFamily_Arms) ===')
tex = np.asarray(Image.open(LIVE / 'T_M4OriginalShape_SkinColourDetail.png').convert('RGB'),
                 dtype=np.float64) / 255.0
lum = tex @ np.array([0.2126, 0.7152, 0.0722])
R['colour_detail_luma'] = angular_energy(lum, 'ColourDetail luma')
R['colour_detail_r'] = angular_energy(tex[..., 0], 'ColourDetail R')

# shader-faithful per-channel albedo factor: lerp(1, 2*tex, STRENGTH)
factor = 1.0 + STRENGTH * (2.0 * tex - 1.0)
fl = factor @ np.array([0.2126, 0.7152, 0.0722])
stats = {}
for name, arr in (('factor_luma', fl), ('factor_r', factor[..., 0])):
    p = np.percentile(arr, [1, 5, 50, 95, 99])
    stats[name] = {'p1': float(p[0]), 'p5': float(p[1]), 'p50': float(p[2]),
                   'p95': float(p[3]), 'p99': float(p[4]),
                   'p99_over_p1': float(p[4] / max(p[0], 1e-9)),
                   'p95_over_p5': float(p[3] / max(p[1], 1e-9)),
                   'frac_below_0.9': float((arr < 0.9).mean()),
                   'frac_above_1.1': float((arr > 1.1).mean())}
    print('  %s: p1 %.3f  p50 %.3f  p99 %.3f  (p95/p5 %.2fx)  '
          'area<0.9 %.1f%%  area>1.1 %.1f%%'
          % (name, p[0], p[2], p[4], stats[name]['p95_over_p5'],
             100 * stats[name]['frac_below_0.9'], 100 * stats[name]['frac_above_1.1']))
R['albedo_factor_stats'] = stats
R['albedo_factor_anisotropy'] = angular_energy(fl, 'albedo factor (luma)')

# smooth the factor like a mip at typical close-up footprint, then re-measure the
# band contrast that actually survives on screen (2-4 texel footprint at extreme close-up)
for sigma in (1.0, 2.0):
    s = gaussian_filter(fl, sigma, mode='wrap')
    p = np.percentile(s, [5, 95])
    R.setdefault('albedo_factor_mipped', {})[str(sigma)] = {
        'p5': float(p[0]), 'p95': float(p[1]), 'p95_over_p5': float(p[1] / max(p[0], 1e-9))}
    print('  factor blurred sigma=%.0f: p5 %.3f p95 %.3f (ratio %.2fx)'
          % (sigma, p[0], p[1], p[1] / max(p[0], 1e-9)))

print('\n=== source COLOR scan (reference) ===')
scan = np.asarray(Image.open(SCAN / 'Skin_Human_002_COLOR.png').convert('RGB'),
                  dtype=np.float64) / 255.0
scan = np.where(scan <= .04045, scan / 12.92, ((scan + .055) / 1.055) ** 2.4)
R['colour_scan_luma'] = angular_energy(scan @ np.array([0.2126, 0.7152, 0.0722]),
                                       'COLOR scan luma (linear)')

print('\n=== sanity: rolled-back SkinMicro height must be directional again (2.12x @62.5) ===')
micro = np.asarray(Image.open(LIVE / 'T_M4OriginalShape_SkinMicro.png'), dtype=np.float64) / 255.0
R['skinmicro_height_b'] = angular_energy(micro[..., 2], 'SkinMicro height (b)')

# preview: albedo factor as if it were the only modulation on mid-brown skin
preview = np.uint8(np.clip((fl[..., None] * np.array([[[0.372, 0.232, 0.182]]])) ** (1 / 2.2) * 255, 0, 255))
Image.fromarray(preview).save(OUT / 'colour_factor_preview.png')

(OUT / 'colour_detail_report.json').write_text(json.dumps(R, indent=2), encoding='utf-8')
print('\nCOLOUR_DETAIL_ANALYSIS_DONE')
