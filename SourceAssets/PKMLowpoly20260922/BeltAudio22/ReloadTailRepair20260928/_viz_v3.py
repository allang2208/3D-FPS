"""Render v3 the same way the installed set was rendered, for a direct visual check.

Same cues, same 1024-pt / 47 Hz bins, same -105..-25 dB scale as
`spectro_coarse.png`, so the two images can be compared panel for panel.  The
question is narrow: does the continuous bright band below ~500 Hz that runs the
whole length of every installed asset survive in v3?
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
NEW = HERE / 'out3'
RATE = 48000

x, _ = sf.read(PARENT / 'reference_audio.wav')
mono = x if x.ndim == 1 else x.mean(axis=1)
mono = sosfiltfilt(butter(2, 80, fs=RATE, btype='highpass', output='sos'), mono)

CUES = ['CoverOpen', 'BeltLift', 'BoxOut', 'BeltSeat', 'CoverClose', 'ChargePullMove']
CHARGE = ('ChargePullMove', 'ChargeRearStop', 'ChargePushMove', 'ChargeFrontStop')


def inst(n):
    p = PARENT / f'S_PKM_{n}.wav'
    return p if p.is_file() else PARENT.parent / 'ChargeAudio35' / f'S_PKM_{n}.wav'
rows = [('BED reference (music only)', mono[round(1.10 * RATE):round(3.25 * RATE)])]
for n in CUES:
    rows.append(('%s  v3' % n, sf.read(NEW / f'S_PKM_{n}_debgm3.wav')[0].astype(np.float64)))
    rows.append(('%s  INSTALLED' % n, sf.read(inst(n))[0].astype(np.float64)))

fig, axes = plt.subplots(len(rows), 1, figsize=(13, 1.5 * len(rows)), dpi=95)
for ax, (title, v) in zip(axes, rows):
    f, t, Z = stft(v, fs=RATE, nperseg=1024, noverlap=768, window='hann',
                   boundary='zeros', padded=True)
    sel = f <= 4000
    S = 20 * np.log10(np.abs(Z[sel]) + 1e-9)
    ax.pcolormesh(t, f[sel], S, shading='nearest', cmap='magma', vmin=-105, vmax=-25)
    ax.set_title(title, fontsize=7.5, loc='left',
                 color='black' if 'v3' in title else 'dimgray')
    ax.set_yticks([0, 500, 1000, 2000, 4000])
    ax.tick_params(labelsize=5.5)
    ax.set_ylabel('Hz', fontsize=6)
axes[-1].set_xlabel('seconds')
fig.tight_layout()
out = HERE / 'spectro_v3.png'
fig.savefig(out)
print('wrote', out, out.stat().st_size)

# numeric companion: mean level of the 0-500 Hz band over the whole cue
print('\nmean level of the 0-500 Hz band (the bed\'s body), installed vs v3:')
for n in CUES:
    res = []
    for tag, p in (('installed', inst(n)),
                   ('v3', NEW / f'S_PKM_{n}_debgm3.wav')):
        v = sf.read(p)[0].astype(np.float64)
        _, _, Z = stft(v, fs=RATE, nperseg=1024, noverlap=768, window='hann',
                       boundary='zeros', padded=True)
        f = np.fft.rfftfreq(1024, 1 / RATE)
        s = (f >= 20) & (f < 500)
        res.append(10 * np.log10(np.mean(np.abs(Z[s]) ** 2) + 1e-30))
    print('  %-16s %7.1f -> %7.1f dB   (%+.1f dB)' % (n, res[0], res[1], res[1] - res[0]))