"""Diagnostic only: independent confirmation of which two clips carry the wind.

Two checks that do not reuse the first metric:
  1. frame-by-frame wind-band level across the whole recording, showing which
     clip windows sit on a genuinely elevated bed;
  2. before/after wind reduction in the raw source, so the residual can be
     stated against what the original pass already achieved.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

HERE = Path(__file__).resolve().parent
OUT = HERE / '_wind'
SR = 48000
WIND_BAND = (250, 1000)

STAGES = [('Open', .305, .555), ('Eject', 1.800, 2.230), ('Retrieve', 2.780, 3.030),
          ('Insert', 3.190, 3.760), ('Release', 3.895, 4.040), ('Withdraw', 4.080, 4.385),
          ('Close', 4.940, 5.420)]
QUIET_SPANS = [(.65, 1.65), (2.28, 2.65), (4.47, 4.82), (5.60, 6.35)]


def wind_env(x, win_ms=50, hop_ms=10):
    sos = signal.butter(3, list(WIND_BAND), fs=SR, btype='bandpass', output='sos')
    w = signal.sosfiltfilt(sos, x, axis=0)
    if w.ndim > 1:
        w = w.mean(axis=1)
    n, h = int(win_ms / 1000 * SR), int(hop_ms / 1000 * SR)
    idx = np.arange(0, max(1, len(w) - n), h)
    env = np.array([np.sqrt(np.mean(w[i:i + n] ** 2)) for i in idx])
    return idx / SR, 20 * np.log10(env + 1e-12)


raw, sr = sf.read(HERE / 'Analysis/715-reloading-decoded.wav', always_2d=True)
clean, _ = sf.read(HERE / 'Cleaned/715-reloading-wind-reduced.wav', always_2d=True)

mono_raw = raw.mean(axis=1)
sos = signal.butter(3, 200, fs=SR, btype='highpass', output='sos')
mono_hp = signal.sosfiltfilt(sos, mono_raw, axis=0)
clean_m = clean.mean(axis=1)

t_hp, env_hp = wind_env(mono_hp)
t_cl, env_cl = wind_env(clean_m)

print('== wind band (250-1000 Hz) level, dBFS ==')
print('%-9s%10s%10s%10s%10s' % ('clip', 'raw HP', 'cleaned', 'reduction', 'note'))
rows = []
for name, a, b in STAGES:
    sel_hp = (t_hp >= a) & (t_hp <= b)
    sel_cl = (t_cl >= a) & (t_cl <= b)
    r = float(np.median(env_hp[sel_hp]))
    c = float(np.median(env_cl[sel_cl]))
    rows.append({'clip': name, 'raw_hp_dbfs': round(r, 1), 'cleaned_dbfs': round(c, 1),
                 'reduction_db': round(r - c, 1)})
for r in rows:
    print('%-9s%10.1f%10.1f%10.1f' % (r['clip'], r['raw_hp_dbfs'], r['cleaned_dbfs'],
                                       r['reduction_db']))
print()
print('%-9s%10s%10s' % ('reference', 'raw HP', 'cleaned'))
for a, b in QUIET_SPANS:
    sel_hp = (t_hp >= a) & (t_hp <= b)
    sel_cl = (t_cl >= a) & (t_cl <= b)
    print('%-9s%10.1f%10.1f' % ('%.2f-%.2f' % (a, b), float(np.median(env_hp[sel_hp])),
                                float(np.median(env_cl[sel_cl]))))

# loudest sustained wind sections in the whole recording
order = np.argsort(env_hp)[::-1]
print()
print('loudest wind frames in the recording (1 s windows, non-overlapping):')
best = []
for start in np.arange(0, t_hp[-1] - 1, .5):
    sel = (t_hp >= start) & (t_hp < start + 1)
    if sel.sum() < 5:
        continue
    best.append((float(np.median(env_hp[sel])), float(start), float(start + 1)))
best.sort(reverse=True)
for level, s, e in best[:6]:
    inside = [n for n, a, b in STAGES if a < e and b > s]
    print('   %+.1f dBFS  %.1f-%.1f s   inside: %s' % (level, s, e, ', '.join(inside) or '-'))

(OUT / 'wind_confirm.json').write_text(
    json.dumps({'per_clip': rows, 'loudest_windows': best[:6]}, indent=2), encoding='utf-8')