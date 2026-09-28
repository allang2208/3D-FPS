"""Diagnostic only: is the contaminated part only the decay tail?

Reconstructs the current clips' envelopes and the local bed estimate to locate
the exact time range where the bed dominates the signal.  That range is the
only place BGM can be heard, and therefore the only thing worth rebuilding.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import stft

HERE = Path(__file__).resolve().parent
RATE = 48000
NP, HOP = 2048, 512
x, rate = sf.read(HERE / 'reference_audio.wav')
mono = x if x.ndim == 1 else x.mean(axis=1)

CLIPS = [('CoverOpen', 10.825, 11.340, [9.05, 10.05], [11.45, 12.45]),
         ('CoverClose', 15.865, 16.100, [15.10, 15.75], [16.20, 17.00])]


def P_of(seg):
    _, _, Z = stft(seg, fs=RATE, nperseg=NP, noverlap=NP - HOP, window='hann',
                   boundary='zeros', padded=True)
    return np.abs(Z) ** 2


report = []
for name, a, b, bedw, bedw2 in CLIPS:
    seg = mono[round(a * RATE):round(b * RATE)]
    # local bed power spectrum (bench: quiet stretches on both sides)
    Ps = []
    for lo, hi in (bedw, bedw2):
        h = mono[round(lo * RATE):round(hi * RATE)]
        f, t, Z = stft(h, fs=RATE, nperseg=NP, noverlap=NP - HOP, window='hann',
                       boundary='zeros', padded=True)
        Ps.append(np.abs(Z) ** 2)
    est = np.percentile(np.concatenate(Ps, axis=1), 70, axis=1)

    f, t, Z = stft(seg, fs=RATE, nperseg=NP, noverlap=NP - HOP, window='hann',
                   boundary='zeros', padded=True)
    P = np.abs(Z) ** 2
    frames_db = 10 * np.log10(np.sum(P, axis=0) + 1e-30)
    bed_db = 10 * np.log10(np.sum(est) + 1e-30)
    ratio = frames_db - bed_db          # >0 => contact dominates the bed
    peak_i = int(np.argmax(frames_db))
    # last frame index where the contact still dominates by >= 6 dB
    dom = np.where(ratio >= 6.0)[0]
    last_dom = int(dom.max()) if len(dom) else peak_i
    # find contiguous dominant run containing the peak
    run_end = peak_i
    while run_end + 1 < len(ratio) and ratio[run_end + 1] >= 3.0:
        run_end += 1
    report.append({
        'clip': name, 'window': [a, b], 'clip_ms': round(len(seg) / RATE * 1000, 1),
        'peak_ms': round(peak_i * HOP / RATE * 1000, 1),
        'bed_level_db': round(float(bed_db), 1),
        'contact_peak_db': round(float(frames_db[peak_i]), 1),
        'peak_over_bed_db': round(float(ratio[peak_i]), 1),
        'contact_contiguous_run_end_ms': round(run_end * HOP / RATE * 1000, 1),
        'last_frame_contact_ge6db_ms': round(last_dom * HOP / RATE * 1000, 1),
        'ratio_db_per_frame': [round(float(v), 1) for v in ratio],
    })
    print(json.dumps({k: v for k, v in report[-1].items() if k != 'ratio_db_per_frame'}))
(HERE / '_diag_rebuild.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

print('\nper-frame contact-over-bed ratio (dB), 10.67 ms per frame:')
for r in report:
    print(f"\n== {r['clip']}  peak at {r['peak_ms']} ms, run ends {r['contact_contiguous_run_end_ms']} ms")
    v = r['ratio_db_per_frame']
    for i in range(0, len(v), 4):
        ms = round(i * 10.667, 1)
        print(f'  {ms:7.1f} ms  ' + ' '.join(f'{x:6.1f}' for x in v[i:i + 4]))