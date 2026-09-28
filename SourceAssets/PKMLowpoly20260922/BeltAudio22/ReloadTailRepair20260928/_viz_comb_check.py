"""Is the horizontal comb in the assets real signal, or a rendering artifact?

The spectrograms show a regular horizontal line stack across the installed assets
that the bed reference does not show.  Regular spacing in frequency means a
periodic waveform in time, which would be a big deal -- but a heavily downsampled
`pcolormesh` can alias the frequency axis into a banded pattern too.  Two
independent checks:

1. a coarse spectrogram (1024-point, ~47 Hz bins, drawn near 1:1 so nothing is
   downsampled) -- an artifact disappears, real content stays;
2. an averaged spectrum as a plain line plot, where a real comb shows as evenly
   spaced peaks.
"""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt, stft

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
RATE = 48000

x, _ = sf.read(PARENT / 'reference_audio.wav')
mono = x if x.ndim == 1 else x.mean(axis=1)
mono = sosfiltfilt(butter(2, 80, fs=RATE, btype='highpass', output='sos'), mono)

SEGS = [
    ('bed 1.10-3.25 s (music only)', mono[round(1.10 * RATE):round(3.25 * RATE)]),
    ('CoverOpen 0.15-0.35 s (comb region)',
     sf.read(PARENT / 'S_PKM_CoverOpen.wav')[0].astype(np.float64)[round(.15 * RATE):round(.35 * RATE)]),
    ('CoverOpen FULL', sf.read(PARENT / 'S_PKM_CoverOpen.wav')[0].astype(np.float64)),
    ('BeltSeat 0.07-0.20 s',
     sf.read(PARENT / 'S_PKM_BeltSeat.wav')[0].astype(np.float64)[round(.07 * RATE):round(.20 * RATE)]),
]

# ---- 1. coarse spectrogram, near 1:1 so the frequency axis is not downsampled
fig, axes = plt.subplots(len(SEGS), 1, figsize=(13, 8), dpi=95)
for ax, (title, v) in zip(axes, SEGS):
    f, t, Z = stft(v, fs=RATE, nperseg=1024, noverlap=768, window='hann',
                   boundary='zeros', padded=True)
    sel = f <= 4000
    S = 20 * np.log10(np.abs(Z[sel]) + 1e-9)
    ax.pcolormesh(t, f[sel], S, shading='nearest', cmap='magma', vmin=-105, vmax=-25)
    ax.set_title(title + '   [1024-pt, 47 Hz bins]', fontsize=8, loc='left')
    ax.set_yticks([0, 500, 1000, 2000, 3000, 4000])
    ax.tick_params(labelsize=6)
axes[-1].set_xlabel('seconds')
fig.tight_layout()
fig.savefig(HERE / 'spectro_coarse.png')
print('wrote', HERE / 'spectro_coarse.png')

# ---- 2. averaged spectra: a real comb = evenly spaced peaks
fig2, ax2 = plt.subplots(figsize=(14, 6), dpi=95)
NP = 16384
for title, v in SEGS:
    n = (len(v) // NP) * NP
    if n < NP:
        v = np.pad(v, (0, NP - len(v)))
        n = NP
    seg = v[:n].reshape(-1, NP)
    P = (np.abs(np.fft.rfft(seg * np.hanning(NP), axis=1)) ** 2).mean(axis=0)
    f = np.fft.rfftfreq(NP, 1 / RATE)
    sel = (f >= 100) & (f <= 6000)
    ax2.semilogx(f[sel], 10 * np.log10(P[sel] + 1e-20), lw=0.6, label=title)
ax2.set_xlim(100, 6000)
ax2.set_ylim(-110, -25)
ax2.grid(True, which='both', alpha=0.25)
ax2.set_xlabel('Hz (log)')
ax2.set_ylabel('dB')
ax2.set_title('averaged spectra, 16384-pt (2.9 Hz bins) -- a real comb shows as evenly spaced peaks')
ax2.legend(fontsize=7)
fig2.tight_layout()
fig2.savefig(HERE / 'spectra_avg.png')
print('wrote', HERE / 'spectra_avg.png')

# numeric: how peaked is the spectrum? count local maxima exceeding neighbours
print('\npeak count and spacing in the averaged spectrum, 200-3000 Hz:')
for title, v in SEGS:
    n = max(NP, (len(v) // NP) * NP)
    vv = v[:n] if len(v) >= NP else np.pad(v, (0, NP - len(v)))
    seg = vv[: (len(vv) // NP) * NP].reshape(-1, NP)
    P = (np.abs(np.fft.rfft(seg * np.hanning(NP), axis=1)) ** 2).mean(axis=0)
    f = np.fft.rfftfreq(NP, 1 / RATE)
    sel = (f >= 200) & (f <= 3000)
    pf, pp = f[sel], 10 * np.log10(P[sel] + 1e-20)
    loc = [i for i in range(2, len(pp) - 2)
           if pp[i] > pp[i - 2] + 1.5 and pp[i] > pp[i + 2] + 1.5 and pp[i] > pp[i - 1] and pp[i] > pp[i + 1]]
    peaks = pf[loc]
    d = np.diff(peaks) if len(peaks) > 1 else np.array([])
    print('  %-40s peaks %3d   median spacing %6.1f Hz   spread %s'
          % (title, len(peaks), np.median(d) if len(d) else 0,
             ('%.1f-%.1f' % (np.percentile(d, 10), np.percentile(d, 90))) if len(d) > 2 else 'n/a'))