"""Diagnostic only: verify the rebuild.

  1. Is the background music actually gone from the rebuilt tail?
     Measured as its third-octave spectrum against a bus-only stretch used as
     the clean reference for this scene.
  2. Is the splice click-free?  Measured as waveform discontinuity (max sample
     step / peak slope) and as the fraction of the jump removed by the xfade.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.ndimage import uniform_filter1d
from scipy.signal import butter, sosfiltfilt, stft

HERE = Path(__file__).resolve().parent
OUT = HERE / 'rebuild'
RATE = 48000
BANDS = [(20, 40), (40, 80), (80, 160), (160, 315), (315, 630), (630, 1250),
         (1250, 2500), (2500, 5000), (5000, 8000), (8000, 14000), (14000, 20000)]

x, rate = sf.read(HERE / 'reference_audio.wav')
mono = x if x.ndim == 1 else x.mean(axis=1)


def band_power(v):
    nfft = 1 << int(np.ceil(np.log2(max(len(v), 4096))))
    P = np.abs(np.fft.rfft(v, nfft)) ** 2
    f = np.fft.rfftfreq(nfft, 1 / RATE)
    return np.array([float(np.sum(P[(f >= lo) & (f < hi)])) + 1e-30 for lo, hi in BANDS])


# clean bed reference for this scene: stretches with no contact at all
bed = np.concatenate([mono[round(a * RATE):round(b * RATE)] for a, b in
                      [(1.10, 3.25), (3.90, 5.00), (6.10, 7.25), (7.65, 8.75),
                       (9.05, 10.00)]])
bed_bp = band_power(bed) / len(bed)
print('clean-bed band power (per sample), dB:',
      [round(10 * np.log10(v + 1e-30), 1) for v in bed_bp])

PLAN = [('CoverOpen', 437.3 / 1000, 0.72), ('CoverClose', 192.0 / 1000, 1.0)]
rows = []
for name, ho_s, tempo in PLAN:
    orig, _ = sf.read(HERE / f'S_PKM_{name}.wav')
    new, _ = sf.read(OUT / f'S_PKM_{name}_rebuilt_delivered.wav')
    old_tail, _ = sf.read(OUT / f'_{name}_removed_tail.wav')
    ho_new = int(round(len(new) * ho_s / (len(orig) * ho_s / len(orig))))  # same ratio
    # delivered length differs by tempo; scale the handover by the same factor
    scale = len(new) / (len(orig) * (1.0))
    ho_new = int(round(ho_s * RATE * (1 / tempo)))
    ho_new = min(ho_new, len(new) - 1)

    rebuilt_tail = np.asarray(new)[ho_new:]
    removed = np.asarray(old_tail)
    bp_new = band_power(rebuilt_tail) / len(rebuilt_tail)
    bp_old = band_power(removed) / len(removed)

    # music-band excess over the clean bed (per band, dB)
    excess_old = [round(10 * np.log10((o + 1e-30) / (b + 1e-30)), 1)
                  for o, b in zip(bp_old, bed_bp)]
    excess_new = [round(10 * np.log10((o + 1e-30) / (b + 1e-30)), 1)
                  for o, b in zip(bp_new, bed_bp)]

    # splice: waveform discontinuity across the join, vs the local slope
    before = np.asarray(new)[ho_new - 8:ho_new]
    after = np.asarray(new)[ho_new:ho_new + 8]
    step = abs(after[0] - before[-1])
    local_slope = float(np.mean(np.abs(np.diff(np.asarray(new)[max(0, ho_new - 200):ho_new + 200]))))
    rows.append({'clip': name, 'handover_ms': round(ho_s * 1000, 1),
                 'rebuilt_tail_ms': round(len(rebuilt_tail) / RATE * 1000, 1),
                 'excess_over_clean_bed_old_tail_db': excess_old,
                 'excess_over_clean_bed_new_tail_db': excess_new,
                 'worst_band_old_db': max(excess_old),
                 'worst_band_new_db': max(excess_new),
                 'splice_sample_step': round(float(step), 6),
                 'local_mean_abs_slope': round(local_slope, 6),
                 'splice_step_in_local_slopes': round(float(step / (local_slope + 1e-12)), 2),
                 'new_tail_peak': round(float(np.max(np.abs(rebuilt_tail))), 5),
                 'old_tail_peak': round(float(np.max(np.abs(removed))), 5)})
    print(json.dumps(rows[-1]))
(OUT / 'verification.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')