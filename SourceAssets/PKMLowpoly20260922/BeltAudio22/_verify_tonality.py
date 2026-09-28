"""Diagnostic only: does the rebuilt tail still contain the music harmonics?

The music is a tonal structure, so the honest test is how much of the local
spectrum sits in narrow peaks around the music's partials, before and after.
A rebuild that reuses the contaminated tail as its colour reference fails here.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.ndimage import uniform_filter1d

HERE = Path(__file__).resolve().parent
RATE = 48000
NPART = [46.9, 117.2, 210.9, 328.1, 515.6, 609.4, 679.7, 820.3, 1031.2]


def tonality(v, label, smooth_bins=9):
    """fraction of spectrum power sitting in narrow peaks; peak heights at partials"""
    nfft = 1 << int(np.ceil(np.log2(max(len(v), 8192))))
    P = np.abs(np.fft.rfft(v * np.hanning(len(v)), nfft)) ** 2
    f = np.fft.rfftfreq(nfft, 1 / RATE)
    sm = uniform_filter1d(P, smooth_bins, mode='nearest')
    sel = (f >= 40) & (f <= 4000)
    peakiness = float(np.sum(np.maximum(P[sel] - sm[sel], 0)) / (np.sum(P[sel]) + 1e-30))
    heights = []
    for hz in NPART:
        m = (f > hz - 8) & (f < hz + 8)
        if m.sum():
            heights.append(round(float(10 * np.log10((P[m].max() + 1e-30)
                                                     / (sm[m].mean() + 1e-30))), 1))
    return {'label': label, 'peakiness': round(peakiness, 4),
            'partial_excess_db': heights,
            'mean_partial_excess_db': round(float(np.mean(heights)), 2)}


rows = []
# reference points
mono, _ = sf.read(HERE / 'reference_audio.wav')
if mono.ndim > 1:
    mono = mono.mean(axis=1)
clean_bed = np.concatenate([mono[round(a * RATE):round(b * RATE)] for a, b in
                            [(1.10, 3.25), (6.10, 7.25), (9.05, 10.00)]])
rows.append(tonality(clean_bed, 'clean bed (1-10 s, no contact)'))
rows.append(tonality(mono[round(25.010 * RATE):round(25.215 * RATE)], 'ChargeRelease donor'))

for name in ('CoverOpen', 'CoverClose'):
    orig, _ = sf.read(HERE / f'S_PKM_{name}.wav')
    rebuilt, _ = sf.read(HERE / f'rebuild/S_PKM_{name}_rebuilt_delivered.wav')
    removed, _ = sf.read(HERE / f'rebuild/_{name}_removed_tail.wav')
    rows.append(tonality(np.asarray(removed), f'{name} OLD tail (contaminated)'))
    rows.append(tonality(np.asarray(rebuilt)[-int(0.030 * RATE):], f'{name} NEW tail (rebuilt, last 30 ms)'))
    rows.append(tonality(np.asarray(orig)[:int(0.30 * RATE)], f'{name} impact prefix (kept)'))

for r in rows:
    print(json.dumps(r))
(Path(HERE) / 'rebuild' / 'tonality.json').write_text(json.dumps(rows, indent=2),
                                                     encoding='utf-8')