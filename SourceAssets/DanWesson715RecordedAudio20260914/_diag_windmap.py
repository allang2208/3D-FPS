"""Diagnostic only: spectrogram map of the 715 reloading recording.

Renders the exposed picture so the wind can be judged directly: time across,
frequency up, with the four spans the original pass treated as "quiet" marked
along with the seven delivered clip windows.

Writes only `_wind/715-wind-map.png` and `_wind/wind_frames.json`.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import soundfile as sf
from scipy import signal

HERE = Path(__file__).resolve().parent
OUT = HERE / '_wind'
OUT.mkdir(exist_ok=True)
SR = 48000
NPERSEG, NOVERLAP = 2048, 1792

STAGES = [
    ('Open', .305, .555), ('Eject', 1.800, 2.230), ('Retrieve', 2.780, 3.030),
    ('Insert', 3.190, 3.760), ('Release', 3.895, 4.040), ('Withdraw', 4.080, 4.385),
    ('Close', 4.940, 5.420),
]
QUIET_SPANS = [(.65, 1.65), (2.28, 2.65), (4.47, 4.82), (5.60, 6.35)]

raw, sr = sf.read(HERE / 'Analysis/715-reloading-decoded.wav', always_2d=True)
mono = raw.mean(axis=1)
sos = signal.butter(3, 200, fs=SR, btype='highpass', output='sos')
mono = signal.sosfiltfilt(sos, mono, axis=0)

f, t, z = signal.stft(mono, fs=SR, nperseg=NPERSEG, noverlap=NOVERLAP, boundary='zeros')
mag = np.abs(z)
db = 20 * np.log10(mag + 1e-10)

fig, axes = plt.subplots(2, 1, figsize=(17, 9), layout='constrained',
                         gridspec_kw={'height_ratios': [3, 2]})
ax = axes[0]
band = (f >= 150) & (f <= 9000)
im = ax.pcolormesh(t, f[band], db[band], shading='auto', cmap='magma',
                   vmin=-96, vmax=-30)
ax.set(yscale='log', ylim=(150, 9000), xlim=(0, len(raw) / SR),
       ylabel='Hz', title='715 reloading recording: 200 Hz high-pass, wind exposed')
for a, b in QUIET_SPANS:
    ax.axvspan(a, b, color='#39ff14', alpha=.10)
    ax.text((a + b) / 2, 7000, 'quiet span', fontsize=7, ha='center', color='#39ff14')
for i, (name, a, b) in enumerate(STAGES):
    ax.axvspan(a, b, color='#00bfff', alpha=.07)
    ax.axvline(a, lw=.7, color='#00bfff', alpha=.6)
    ax.axvline(b, lw=.7, color='#00bfff', alpha=.6)
    ax.text((a + b) / 2, 200, name, fontsize=8, ha='center', color='#00bfff', rotation=90)
fig.colorbar(im, ax=ax, label='dB')
ax.grid(alpha=.15, which='both')

ax = axes[1]
frame_db = 10 * np.log10(np.sum(mag ** 2, axis=0) + 1e-20)
ax.plot(t, frame_db, lw=.7, color='#365879')
for a, b in QUIET_SPANS:
    ax.axvspan(a, b, color='#39ff14', alpha=.10)
for name, a, b in STAGES:
    ax.axvspan(a, b, color='#00bfff', alpha=.07)
    ax.text((a + b) / 2, frame_db.max() - 4, name, fontsize=8, ha='center', color='#1f4e79',
            rotation=90)
ax.set(xlim=(0, len(raw) / SR), ylabel='frame power dB', xlabel='Seconds')
ax.grid(alpha=.2)
fig.savefig(OUT / '715-wind-map.png', dpi=130)

# per-clip quiet-frame floor, in the low-mid bands where wind reads loudest
rows = []
for name, a, b in STAGES:
    sel = (t >= a) & (t <= b)
    if not sel.any():
        continue
    lo = (f >= 300) & (f < 2000)
    fr = 10 * np.log10(np.sum(mag[:, sel] ** 2, axis=0) + 1e-20)
    floor_idx = np.argsort(fr)[:max(1, int(round(.25 * len(fr))))]
    floor_db = float(np.mean(fr[floor_idx]))
    rows.append({'clip': name, 'frames': int(sel.sum()),
                 'quietest_quartile_dbfs': round(floor_db, 1),
                 'median_dbfs': round(float(np.median(fr)), 1)})

ref = []
for a, b in QUIET_SPANS:
    sel = (t >= a) & (t <= b)
    fr = 10 * np.log10(np.sum(mag[:, sel] ** 2, axis=0) + 1e-20)
    ref.append(float(np.median(fr)))
print('quiet-span median frame dB:', [round(v, 1) for v in ref])
print('mean quiet-span floor dB :', round(float(np.mean(ref)), 1))
for r in rows:
    r['excess_over_quiet_spans_db'] = round(r['quietest_quartile_dbfs'] - float(np.mean(ref)), 1)
    print('  %-9s frames %3d  quietest-quartile %7.1f dB  median %7.1f dB  excess %+5.1f dB'
          % (r['clip'], r['frames'], r['quietest_quartile_dbfs'], r['median_dbfs'],
             r['excess_over_quiet_spans_db']))
(OUT / 'wind_frames.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')