"""A coarse level map of the whole reference video, so music can be told from handling.

The 63 dB spread in the bed band means "one global bed level" was never a valid
floor.  Before trusting any local maximum as *music*, it has to be separated from
the gun handling, which also lives in 250-1000 Hz -- so print both the bed band
and a high band (>2 kHz, where the mechanical contacts have most of their energy)
on the same time base, at 0.5 s resolution.  Music shows as bed-band energy with
little high-band energy and a sustained plateau; handling shows as a short spike
in both.  Cue windows are marked so a swell that lands inside one is visible.
"""
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt, stft

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
RATE, NP, HOP = 48000, 2048, 512
STEP = 0.5

CUES = [('CoverOpen', 10.825, 11.340), ('BeltLift', 11.745, 12.185),
        ('BoxOut', 12.420, 12.900), ('BoxInsert', 14.245, 14.470),
        ('BeltSeat', 15.230, 15.435), ('CoverClose', 15.865, 16.100),
        ('ChargePullMove', 24.180, 24.710), ('ChargeRearStop', 24.710, 24.905),
        ('ChargePushMove', 24.905, 25.010), ('ChargeFrontStop', 25.010, 25.225)]

x, _ = sf.read(PARENT / 'reference_audio.wav')
mono = x if x.ndim == 1 else x.mean(axis=1)
mono = sosfiltfilt(butter(2, 80, fs=RATE, btype='highpass', output='sos'), mono)

_, _, Z = stft(mono, fs=RATE, nperseg=NP, noverlap=NP - HOP, window='hann',
               boundary='zeros', padded=True)
f = np.fft.rfftfreq(NP, 1 / RATE)
P = np.abs(Z) ** 2
lf = P[(f >= 250) & (f < 1000)].sum(axis=0)
hf = P[f >= 2000].sum(axis=0)
allp = P.sum(axis=0)
t = np.arange(len(lf)) * HOP / RATE
n = int(STEP * RATE / HOP)

print('t(s)   LF250-1000   HF>2k    LF-HF   bar(LF, 1 char = 2 dB from -90)   cue')
print('-' * 92)
for s in range(0, len(lf) - n, n):
    t0 = t[s]
    L = 10 * np.log10(lf[s:s + n].mean() + 1e-30)
    H = 10 * np.log10(hf[s:s + n].mean() + 1e-30)
    A = 10 * np.log10(allp[s:s + n].mean() + 1e-30)
    bars = int(max(0, min(40, (L + 90) / 2)))
    hit = [c[0] for c in CUES if not (c[2] < t0 or c[1] > t0 + STEP)]
    print('%5.1f  %9.1f  %8.1f  %6.1f   %-40s %s'
          % (t0, L, H, L - H, '#' * bars, ','.join(hit)))

n_cue = sum(1 for c in CUES for s in range(0, len(lf) - n, n)
            if not (c[2] < t[s] or c[1] > t[s] + STEP))
print('\nblocks containing a cue window: %d of %d' % (n_cue, len(range(0, len(lf) - n, n))))