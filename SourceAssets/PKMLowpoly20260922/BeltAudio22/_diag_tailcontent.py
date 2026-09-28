"""Diagnostic only: what exactly is in the contaminated tail, and is it rebuildable?

For the exposed tail of each clip, measures length, level, spectral centroid and
decay shape.  A rebuild is only worth proposing if that tail is short and simple.
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

# exposed tail = from where the contact stops dominating, to the end of the clip
TAILS = [('CoverOpen', 10.825, 11.340, 405.3),
         ('CoverClose', 15.865, 16.100, 181.3)]

report = []
for name, a, b, t_ms in TAILS:
    seg = mono[round(a * RATE):round(b * RATE)]
    i0 = int(t_ms / 1000 * RATE)
    tail = seg[i0:]
    f, t, Z = stft(tail, fs=RATE, nperseg=1024, noverlap=768, window='hann')
    P = np.mean(np.abs(Z) ** 2, axis=1)
    tot = float(np.sum(P))
    # spectral centroid weighted by power
    cent = float(np.sum(f * P) / tot)
    # octave band shares
    bands = {}
    for lo, hi in [(0, 110), (110, 250), (250, 500), (500, 1000), (1000, 2000),
                   (2000, 4000), (4000, 8000), (8000, 20000)]:
        m = (f >= lo) & (f < hi)
        bands[f'{lo}-{hi}'] = round(100 * float(np.sum(P[m])) / tot, 2)
    # decay: 5 ms rms profile relative to its own start
    step = int(0.005 * RATE)
    prof = [round(float(np.sqrt(np.mean(tail[i:i + step] ** 2))), 6)
            for i in range(0, len(tail) - step, step)]
    report.append({'clip': name, 'tail_start_ms': t_ms,
                   'tail_ms': round(len(tail) / RATE * 1000, 1),
                   'tail_rms_dbfs': round(float(20 * np.log10(np.sqrt(np.mean(tail ** 2)))), 2),
                   'spectral_centroid_hz': round(cent, 1),
                   'band_share_pct': bands,
                   'decay_profile_5ms': prof,
                   'decay_db_from_start': [round(float(20 * np.log10((v + 1e-12) / (prof[0] + 1e-12))), 1)
                                           for v in prof]})
    print(json.dumps({k: v for k, v in report[-1].items()
                      if k not in ('decay_profile_5ms',)}))
(HERE / '_diag_tailcontent.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

# What clean mechanical material exists to rebuild from?  the other contacts
print('\navailable clean-ish mechanical events (masking margin vs bed):')
EVENTS = [('CoverOpen_body', 10.825, 11.230), ('BeltLift', 11.745, 12.185),
          ('BoxOut', 12.420, 12.900), ('BoxInsert', 14.245, 14.470),
          ('BeltSeat', 15.230, 15.435), ('CoverClose_body', 15.865, 16.050),
          ('ChargePull', 24.710, 24.935), ('ChargeRelease', 25.010, 25.215)]
for nm, a, b in EVENTS:
    seg = mono[round(a * RATE):round(b * RATE)]
    print(f'  {nm:18s} {len(seg)/RATE*1000:6.1f} ms  rms '
          f'{20*np.log10(np.sqrt(np.mean(seg**2))):6.1f} dBFS  '
          f'peak {20*np.log10(np.max(np.abs(seg))):6.1f} dBFS')