"""Diagnostic only: locate exposed wind in the 715 speedloader clips.

The delivered clips were authored with a 200 Hz high-pass plus a soft spectral
mask whose noise profile came from four "quiet spans".  Wind survives wherever
the mechanical transient does not mask it: in the pre-roll and the release tail.

For each clip this measures the level in its own quietest frames, per band, and
compares it with the global quiet-span floor of the same recording.  Wind is
broadband and low-mid weighted, so an excess that is flat-ish across bands is
wind rather than mechanism.

Nothing is written outside `_wind/`; no delivered file is touched.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

HERE = Path(__file__).resolve().parent
OUT = HERE / '_wind'
OUT.mkdir(exist_ok=True)
SR = 48000
NPERSEG, NOVERLAP = 2048, 1792

STAGES = [
    ('Open', .305, .555, .4125),
    ('Eject', 1.800, 2.230, 2.0575),
    ('Retrieve', 2.780, 3.030, 2.8475),
    ('Insert', 3.190, 3.760, 3.6125),
    ('Release', 3.895, 4.040, 3.9375),
    ('Withdraw', 4.080, 4.385, 4.2825),
    ('Close', 4.940, 5.420, 5.0075),
]
QUIET_SPANS = [(.65, 1.65), (2.28, 2.65), (4.47, 4.82), (5.60, 6.35)]
BANDS = [(200, 400), (400, 800), (800, 1600), (1600, 3200), (3200, 6400), (6400, 12000)]

raw, sr = sf.read(HERE / 'Analysis/715-reloading-decoded.wav', always_2d=True)
assert sr == SR, sr


def hp(x, hz=200):
    sos = signal.butter(3, hz, fs=SR, btype='highpass', output='sos')
    return signal.sosfiltfilt(sos, x, axis=0)


def stft_power(x):
    f, t, z = signal.stft(x.T, fs=SR, nperseg=NPERSEG, noverlap=NOVERLAP, boundary='zeros')
    return f, t, np.mean(np.abs(z) ** 2, axis=0)


def band_sum(power, f, frame_mask):
    if frame_mask is None:
        sel = power
    else:
        sel = power[:, frame_mask]
    out = []
    for lo, hi in BANDS:
        rows = (f >= lo) & (f < hi)
        out.append(float(np.sum(sel[rows])) if sel.size else 0.0)
    return np.array(out)


def to_db(v):
    return [round(float(10 * np.log10(x + 1e-30)), 1) for x in v]


f, t, P = stft_power(hp(raw))

quiet_mask = np.zeros(len(t), dtype=bool)
for a, b in QUIET_SPANS:
    quiet_mask |= (t >= a) & (t <= b)
noise_profile = np.quantile(P[:, quiet_mask], .65, axis=1)
noise_band = band_sum(noise_profile[:, None], f, None)

print('bands            :', '  '.join('%d-%d' % b for b in BANDS))
print('global noise dB  :', to_db(noise_band))
print()

rows = []
for name, a, b, anchor in STAGES:
    y = hp(raw[round(a * SR):round(b * SR)])
    _, tc, Pc = stft_power(y)
    frame_db = 10 * np.log10(Pc.sum(axis=0) + 1e-20)
    quiet_frames = frame_db < (np.percentile(frame_db, 95) - 20)
    if quiet_frames.sum() < 3:
        quiet_frames = frame_db <= np.percentile(frame_db, 30)
    quiet_energy = band_sum(Pc, f, quiet_frames)
    ratio_db = [round(float(10 * np.log10((quiet_energy[i] + 1e-30) /
                                          (noise_band[i] + 1e-30))), 1)
                for i in range(len(BANDS))]
    wav, _ = sf.read(HERE / ('Waves/S_DW715_Loader_%s.wav' % name))
    rows.append({
        'clip': name,
        'span_s': [a, b],
        'duration_ms': round((b - a) * 1000, 1),
        'peak_dbfs': round(float(20 * np.log10(float(np.max(np.abs(wav))) + 1e-12)), 2),
        'quiet_band_db': to_db(quiet_energy),
        'quiet_over_global_noise_db': ratio_db,
        'flat_excess_db': round(float(np.mean(ratio_db[1:5])), 1),
        'quiet_frames': int(quiet_frames.sum()),
    })

print('%-10s%8s%8s  %s' % ('clip', 'dur_ms', 'peak', 'quiet band excess over global noise (dB)'))
print('%-10s%8s%8s  %s' % ('', '', '', '  '.join('%d-%d' % b for b in BANDS)))
for r in rows:
    print('%-10s%8.1f%8.2f  %s' % (r['clip'], r['duration_ms'], r['peak_dbfs'],
                                   '  '.join('%6.1f' % v for v in r['quiet_over_global_noise_db'])))
print()
print('ranked by broadband (400-3200 Hz) excess:')
for r in sorted(rows, key=lambda x: -x['flat_excess_db']):
    print('   %-10s %+5.1f dB' % (r['clip'], r['flat_excess_db']))

(OUT / 'wind_scan.json').write_text(
    json.dumps({'bands': BANDS, 'global_noise_db': to_db(noise_band), 'rows': rows}, indent=2),
    encoding='utf-8')