"""Diagnostic only: characterise background music in the reference decode.

Reads the already-decoded reference_audio.wav, reports band levels over time and
dumps the spectra of the two suspect contact clips. Nothing is written back to
deliverable audio.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt, stft

HERE = Path(__file__).resolve().parent
RATE = 48000
x, rate = sf.read(HERE / 'reference_audio.wav')
assert rate == RATE, rate
mono = x if x.ndim == 1 else x.mean(axis=1)
print(f'decoded: {len(mono)} samples, {len(mono)/RATE:.3f} s, ndim={x.ndim}')

# ---- 1. Long-term band energy profile: where is music, where is it quiet? ----
band_edges = [20, 80, 200, 500, 1200, 3000, 6000, 12000, 20000]
def band_rms(sig, lo, hi):
    sos = butter(4, [lo, hi], fs=RATE, btype='bandpass', output='sos')
    return float(np.sqrt(np.mean(sosfiltfilt(sos, sig) ** 2)))

win = int(0.25 * RATE)
frames = []
for i in range(0, len(mono) - win, win):
    seg = mono[i:i + win]
    frames.append([round(float(np.sqrt(np.mean(seg ** 2))), 5)]
                  + [round(band_rms(seg, band_edges[b], band_edges[b + 1]), 5)
                     for b in range(len(band_edges) - 1)])

# ---- 2. Spectrum of the two suspect clips ----
SUSPECT = [('CoverOpen', 10.825, 11.340), ('CoverClose', 15.865, 16.100)]

def spectrum_stats(a, b, label):
    seg = mono[round(a * RATE):round(b * RATE)].copy()
    f, t, Z = stft(seg, fs=RATE, nperseg=1024, noverlap=768, window='hann')
    mag = np.abs(Z)
    out = {'label': label, 'window': [a, b], 'duration': round(len(seg) / RATE, 4),
           'rms': round(float(np.sqrt(np.mean(seg ** 2))), 5),
           'peak': round(float(np.max(np.abs(seg))), 5)}
    # per-100 Hz band share over the whole clip
    shares = {}
    for lo in range(0, 8000, 250):
        m = (f >= lo) & (f < lo + 250)
        shares[str(lo)] = round(float(np.sum(mag[m] ** 2)), 4)
    tot = sum(shares.values()) or 1.0
    out['band_share_pct'] = {k: round(100 * v / tot, 2) for k, v in shares.items()}
    # temporal stationarity: how much energy sits in near-steady frames
    frame_energy = np.sum(mag ** 2, axis=0)
    med = float(np.median(frame_energy))
    out['frame_energy_median'] = med
    out['frames'] = len(t)
    out['tonal_sustain_ratio'] = round(float(np.mean(frame_energy > med) ), 4)
    return out, f, mag, t

report = {'band_edges_hz': band_edges, 'frame_seconds': 0.25, 'frames': frames,
          'suspects': []}
for name, a, b in SUSPECT:
    st, f, mag, t = spectrum_stats(a, b, name)
    report['suspects'].append(st)
    print(json.dumps(st, indent=2))

(HERE / '_diag_bgm.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

# ---- 3. Find the quietest 0.5 s windows in the whole file: candidate BGM-only ----
qwin = int(0.5 * RATE)
rms_all = np.array([np.sqrt(np.mean(mono[i:i + qwin] ** 2))
                    for i in range(0, len(mono) - qwin, qwin // 4)])
order = np.argsort(rms_all)[:25]
print('\nquietest 0.5 s windows (t, rms):')
print([(round(float(i * qwin / 4 / RATE), 3), round(float(rms_all[i]), 5)) for i in order])