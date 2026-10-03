"""Where does the directional grain actually come from?  Measure, do not eyeball.

A downsampled preview can invent apparent direction, so this quantifies orientation
directly from the data: the 2D power spectrum's angular energy distribution, plus the
gradient-orientation histogram.  An isotropic field spreads energy evenly over angle;
a comb/streak field concentrates it.

Decomposes the RefinedSkinV3 height field into its two authored contributors -
the high-passed CC0 scan and the SmoothSkinV2 pore field - and measures each alone.
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

BASE = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ModularOutfit20260924\OriginalShapeBareM4')
SMOOTH = BASE / 'SmoothSkinV2'
REFINED = BASE / 'RefinedSkinV3'
SCAN = REFINED / 'External' / 'SkinHuman002' / 'Skin_Human_002_DISP.png'


def anisotropy(field, label):
    """Angular energy concentration of the power spectrum, 0 = isotropic."""
    f = field - field.mean()
    win = np.hanning(f.shape[0])[:, None] * np.hanning(f.shape[1])[None, :]
    F = np.fft.fftshift(np.abs(np.fft.fft2(f * win)) ** 2)
    n0, n1 = f.shape
    cy, cx = n0 // 2, n1 // 2
    y, x = np.mgrid[0:n0, 0:n1]
    r = np.hypot(y - cy, x - cx)
    th = np.arctan2(y - cy, x - cx) % np.pi          # direction, mod 180 deg
    m = (r > n0 * 0.02) & (r < n0 * 0.45)            # ignore DC and corners
    e = F[m]
    t = th[m]
    bins = np.linspace(0, np.pi, 37)
    idx = np.clip(np.digitize(t, bins) - 1, 0, 35)
    ang = np.bincount(idx, weights=e, minlength=36)
    ang /= max(ang.sum(), 1e-30)
    iso = 1.0 / 36.0
    peak = ang.max() / iso
    # orientation of the strongest band, in degrees measured from +x
    best = np.argmax(ang)
    deg = np.degrees(0.5 * (bins[best] + bins[best + 1]))
    # how much of the energy sits in the top 3 of 36 sectors
    top3 = np.sort(ang)[-3:].sum() / iso / 3.0
    print('  %-26s peak/iso %5.2fx @ %5.1f deg   top3-sector conc %5.2fx   '
          'energy spread(entropy) %.3f'
          % (label, peak, deg, top3, -(ang * np.log(ang + 1e-12)).sum() / np.log(36)))
    return {'peak_over_iso': float(peak), 'peak_angle_deg': float(deg),
            'top3_concentration': float(top3)}


R = {}
print('=== SmoothSkinV2: the pore field alone (what option A changed) ===')
pores = np.load(SMOOTH / 'SkinPores_HeightCm.npy').astype(np.float64)
print('  shape %s  range %.5f..%.5f cm' % (pores.shape, pores.min(), pores.max()))
R['pores'] = anisotropy(pores, 'SmoothV2 pores')

print('\n=== RefinedSkinV3: the final baked height field ===')
final = np.load(REFINED / 'SkinPores_HeightCm.npy').astype(np.float64)
print('  shape %s  range %.5f..%.5f cm' % (final.shape, final.min(), final.max()))
R['final'] = anisotropy(final, 'RefinedV3 final height')

print('\n=== the CC0 scan, high-passed exactly as the baker does it ===')
size, tile_cm = 2048, 8.0
raw = np.asarray(Image.open(SCAN).convert('L'), dtype=np.float64) / 255
lo, hi = np.percentile(raw, [1, 99])
field = np.clip((raw - lo) / (hi - lo), 0, 1)
print('  scan raw: mean %.4f  std %.5f  p1 %.4f  p99 %.4f'
      % (raw.mean(), raw.std(), lo, hi))
hp = field - gaussian_filter(field, 38, mode='wrap')
print('  after high-pass: std %.5f  p99|hp| %.5f  ->  amplified %.1fx by the normalise'
      % (hp.std(), np.percentile(np.abs(hp), 99),
         np.percentile(np.abs(hp), 99) / max(hp.std(), 1e-12)))
R['scan_raw'] = anisotropy(raw, 'scan (raw)')
R['scan_hp'] = anisotropy(hp, 'scan (high-passed)')

print('\n=== decomposition of the final field ===')
p = np.tile(pores, (4, 4)).reshape(size, 2, size, 2).mean(axis=(1, 3))
scan_part = np.clip(hp / max(float(np.percentile(np.abs(hp), 99)), .01), -1, 1) * .0038
print('  scan part  p-p %.5f cm  (%.1f%% of p-p)'
      % (scan_part.max() - scan_part.min(),
         100 * (scan_part.max() - scan_part.min()) / (final.max() - final.min())))
print('  pore part  p-p %.5f cm  (%.1f%% of p-p)'
      % ((p * .60).max() - (p * .60).min(),
         100 * ((p * .60).max() - (p * .60).min()) / (final.max() - final.min())))
R['scan_part'] = anisotropy(scan_part, 'scan component (.0038)')
R['pore_part'] = anisotropy(p * .60, 'pore component (.60)')

print('\n=== VERDICT ===')
for k, v in R.items():
    tag = 'DIRECTIONAL' if v['peak_over_iso'] > 1.6 else 'isotropic'
    print('  %-14s peak/iso %5.2fx @ %5.1f deg  -> %s'
          % (k, v['peak_over_iso'], v['peak_angle_deg'], tag))

out = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922\Sprint47')
(out / 'grain_anisotropy.json').write_text(json.dumps(R, indent=2), encoding='utf-8')
print('\nGRAIN_ANISOTROPY_DONE')