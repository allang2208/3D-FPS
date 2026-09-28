"""Render spectrograms of what is installed, next to the bed alone, and look at them.

Every conclusion so far came from scalar numbers -- margins, band ratios, RMS --
and two rounds of rebuilds were designed from those numbers and both failed.  The
user hears "several notes of the BGM mixed in", which is a *spectral* claim: music
reads as sustained narrowband ridges.  That is directly visible in a spectrogram
and invisible in a band-energy ratio, so render it and look.

Panels: the bed reference alone (music, no handling), then each installed reload
asset, all on the same 0-4 kHz / dB scale so ridges can be compared by eye.
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
NP, HOP = 4096, 256          # 11.7 Hz bins, 5.3 ms hop
FMAX = 4000

x, _ = sf.read(PARENT / 'reference_audio.wav')
mono = x if x.ndim == 1 else x.mean(axis=1)
mono = sosfiltfilt(butter(2, 80, fs=RATE, btype='highpass', output='sos'), mono)

ORDER = ['CoverOpen', 'BeltLift', 'BoxOut', 'BoxInsert', 'BeltSeat', 'CoverClose']
BED = (1.10, 3.25)


def spec(v):
    f, t, Z = stft(v, fs=RATE, nperseg=NP, noverlap=NP - HOP, window='hann',
                   boundary='zeros', padded=True)
    sel = f <= FMAX
    return f[sel], t, 20 * np.log10(np.abs(Z[sel]) + 1e-9)


panels = [('BED reference (1.10-3.25 s, music only)', mono[round(BED[0] * RATE):round(BED[1] * RATE)])]
for n in ORDER:
    panels.append(('%s  (installed)' % n, sf.read(PARENT / f'S_PKM_{n}.wav')[0].astype(np.float64)))

fig, axes = plt.subplots(len(panels), 1, figsize=(15, 2.0 * len(panels)), dpi=88)
for ax, (title, v) in zip(axes, panels):
    f, t, S = spec(v)
    ax.pcolormesh(t, f, S, shading='nearest', cmap='magma', vmin=-105, vmax=-25)
    ax.set_ylabel('Hz', fontsize=7)
    ax.set_title(title, fontsize=8, loc='left')
    ax.set_yticks([0, 500, 1000, 2000, 3000, 4000])
    ax.tick_params(labelsize=6)
axes[-1].set_xlabel('seconds', fontsize=8)
fig.suptitle('installed PKM reload assets vs the music bed alone  (same dB scale)', fontsize=10)
fig.tight_layout(rect=(0, 0, 1, 0.985))
out = HERE / 'spectro_installed.png'
fig.savefig(out)
print('wrote', out, out.stat().st_size)

# also: raw cuts for contrast, and the bed at higher resolution around its partials
fig2, axes2 = plt.subplots(3, 1, figsize=(14, 7.5), dpi=95)
for ax, (title, v) in zip(axes2, [
        ('bed 1.10-3.25 s', mono[round(1.10 * RATE):round(3.25 * RATE)]),
        ('coverOpen INSTALLED', sf.read(PARENT / 'S_PKM_CoverOpen.wav')[0].astype(np.float64)),
        ('beltSeat INSTALLED', sf.read(PARENT / 'S_PKM_BeltSeat.wav')[0].astype(np.float64))]):
    f, t, S = spec(v)
    ax.pcolormesh(t, f, S, shading='nearest', cmap='magma', vmin=-105, vmax=-25)
    ax.set_title(title, fontsize=9, loc='left')
    ax.set_yticks([0, 250, 500, 750, 1000, 1500, 2000])
    ax.tick_params(labelsize=7)
axes2[-1].set_xlabel('seconds')
fig2.tight_layout()
out2 = HERE / 'spectro_zoom.png'
fig2.savefig(out2)
print('wrote', out2, out2.stat().st_size)