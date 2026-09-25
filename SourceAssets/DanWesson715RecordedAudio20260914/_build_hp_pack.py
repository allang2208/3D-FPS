"""Build the A/B pack for the DW715 wind fix (800 Hz high-pass vs delivered).

Also renders a 400 Hz middle option so the amount of low end removed can be
judged rather than taken on trust.  Looped and peak-normalised for comparison.
Writes only into `rebuild/_listening/`.
"""
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

HERE = Path(__file__).resolve().parent
OUT = HERE / 'rebuild' / '_listening'
OUT.mkdir(parents=True, exist_ok=True)
SR = 48000
WINDOWS = {'Eject': (1.800, 2.230, .46), 'Close': (4.940, 5.420, .58)}

raw, sr = sf.read(HERE / 'Analysis/715-reloading-decoded.wav', always_2d=True)


def norm(y, target=-6.0):
    return y * (10 ** (target / 20) / max(float(np.max(np.abs(y))), 1e-12))


def hp(x, hz):
    return signal.sosfiltfilt(signal.butter(4, hz, fs=SR, btype='highpass', output='sos'), x, axis=0)


def lvl(v):
    return round(float(20 * np.log10(np.sqrt(np.mean(np.asarray(v) ** 2)) + 1e-12)), 1)


rows = []
for name, (a, b, target) in WINDOWS.items():
    seg = raw[round(a * SR):round(b * SR)]
    delivered, _ = sf.read(HERE / ('Waves/S_DW715_Loader_%s.wav' % name))
    delivered = np.asarray(delivered)
    fix = hp(seg, 800)
    fix *= target / max(float(np.max(np.abs(fix))), 1e-12)
    mid = hp(seg, 400)
    mid *= target / max(float(np.max(np.abs(mid))), 1e-12)

    sf.write(OUT / f'1_{name}_BEFORE_delivered.wav', np.tile(norm(delivered), 3), SR, subtype='PCM_16')
    sf.write(OUT / f'2_{name}_AFTER_800Hz.wav', np.tile(norm(fix), 3), SR, subtype='PCM_16')
    sf.write(OUT / f'3_{name}_middle_400Hz.wav', np.tile(norm(mid), 3), SR, subtype='PCM_16')
    n = min(len(delivered), len(fix))
    sf.write(OUT / f'4_{name}_removed_lowband.wav',
             np.tile(norm(delivered[:n] - fix[:n]), 6), SR, subtype='PCM_16')
    sf.write(OUT / f'5_{name}_kept_highband.wav', np.tile(norm(fix), 6), SR, subtype='PCM_16')
    rows.append({'clip': name,
                 'delivered_rms': lvl(delivered), 'fix_rms': lvl(fix), 'mid_rms': lvl(mid),
                 'delivered_removed_rms': lvl(delivered[:n] - fix[:n])})

for r in rows:
    print(r)
print()
for p in sorted(OUT.glob('*.wav')):
    print('  ', p.name, p.stat().st_size)