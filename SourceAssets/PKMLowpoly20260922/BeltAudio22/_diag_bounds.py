"""Diagnostic only: exact rebuild boundaries by a single criterion.

A frame is "keepable" when the contact sits >= 6 dB above the bed; a frame is
"contaminated" when it is within 6 dB of the bed (music audible).  Prints the
last keepable frame, so the rebuild hands over only where the music really wins.
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

BED_WIN = [(1.10, 3.25), (3.90, 5.00), (6.10, 7.25), (7.65, 8.75), (9.05, 10.00)]
TARGETS = [('CoverOpen', 10.825, 11.340), ('CoverClose', 15.865, 16.100)]


def P_of(seg):
    _, _, Z = stft(seg, fs=RATE, nperseg=NP, noverlap=NP - HOP, window='hann',
                   boundary='zeros', padded=True)
    return np.abs(Z) ** 2


bed_db = 10 * np.log10(np.sum(np.percentile(
    np.concatenate([P_of(mono[round(a * RATE):round(b * RATE)]) for a, b in BED_WIN],
                   axis=1), 70, axis=1)) + 1e-30)
out = []
for name, a, b in TARGETS:
    seg = mono[round(a * RATE):round(b * RATE)]
    _, _, Z = stft(seg, fs=RATE, nperseg=NP, noverlap=NP - HOP, window='hann',
                   boundary='zeros', padded=True)
    P = np.abs(Z) ** 2
    margin = 10 * np.log10(np.sum(P, axis=0) + 1e-30) - bed_db
    keep = margin >= 6.0
    # walk back from the last keepable frame to find the handover
    last_keep = int(np.max(np.where(keep)[0]))
    out.append({'clip': name, 'bed_db': round(float(bed_db), 1),
                'frame_ms': round(HOP / RATE * 1000, 3),
                'n_frames': len(margin),
                'last_keepable_frame': last_keep,
                'handover_ms': round(last_keep * HOP / RATE * 1000, 1),
                'rebuild_ms': round((len(margin) - 1 - last_keep) * HOP / RATE * 1000, 1),
                'margins_db': [round(float(v), 1) for v in margin],
                'contaminated_from_frame': last_keep + 1})
    print(json.dumps({k: v for k, v in out[-1].items() if k != 'margins_db'}))
    print('   margins from frame 50 ms onward:',
          [f'{round(i*HOP/RATE*1000)}:{v}' for i, v in enumerate(out[-1]['margins_db'])
           if i * HOP / RATE >= 0.05])
(HERE / '_diag_bounds.json').write_text(json.dumps(out, indent=2), encoding='utf-8')