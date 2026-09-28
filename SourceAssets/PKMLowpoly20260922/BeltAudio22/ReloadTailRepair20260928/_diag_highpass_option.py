"""Evaluate a highpass fix against the rebuild, on one audibility criterion.

`_diag_bed_band.py` found the bed is a low-mid hum: 78 % of its energy is in
250-1000 Hz for the reload cuts and 90 % for the charge cuts, while the
mechanical impacts keep their peak above 1-2 kHz (a 1200 Hz highpass costs
0-2.4 dB of peak, 2000 Hz costs 0-4 dB).  That is the DW715 shape exactly --
contaminant in a band, mechanism broadband -- and that case was solved by moving
the highpass, not by rebuilding.

Its margin table was unreadable because ChargePushMove contains digital silence
(log of zero, -300 dB).  This version excludes silent frames and, more usefully,
reports the number that actually predicts audibility:

    residual = bed level in the passband  -  the clip's own peak

i.e. how far below the impact the leftover music sits.  Rendered for the raw
cuts (worst case) and for the current delivered assets (what the user hears).
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt, stft

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
ROOT = PARENT.parent
RATE, NP, HOP = 48000, 1024, 256
SILENT_DB = -90.0

RELOAD = [('CoverOpen', 10.825, 11.340), ('BeltLift', 11.745, 12.185),
          ('BoxOut', 12.420, 12.900), ('BoxInsert', 14.245, 14.470),
          ('BeltSeat', 15.230, 15.435), ('CoverClose', 15.865, 16.100)]
CHARGE = [('ChargePullMove', 24.180, 24.710), ('ChargeRearStop', 24.710, 24.905),
          ('ChargePushMove', 24.905, 25.010), ('ChargeFrontStop', 25.010, 25.225)]
BED_WIN = {'reload': [(1.10, 3.25), (3.90, 5.00), (6.10, 7.25), (7.65, 8.75), (9.05, 10.00)],
           'charge': [(16.00, 16.50), (16.50, 17.00), (17.00, 17.50)]}

x, _ = sf.read(PARENT / 'reference_audio.wav')
mono = x if x.ndim == 1 else x.mean(axis=1)
freqs = np.fft.rfftfreq(NP, 1 / RATE)


def spec(sig):
    _, _, Z = stft(sig, fs=RATE, nperseg=NP, noverlap=NP - HOP, window='hann',
                   boundary='zeros', padded=True)
    return np.abs(Z) ** 2


def hp(sig, corner):
    if not corner:
        return sig
    return sosfilt(butter(4, corner, fs=RATE, btype='highpass', output='sos'), sig)


bed_psd = {}
for group, wins in BED_WIN.items():
    bed_psd[group] = np.mean([spec(mono[round(a * RATE):round(b * RATE)]).mean(axis=1)
                              for a, b in wins], axis=0)


def raw_path(group, name):
    return (PARENT / f'S_PKM_{name}.wav') if group == 'reload' \
        else (ROOT / 'ChargeAudio35' / f'S_PKM_{name}.wav')


repaired = {r['asset_name']: PARENT / r['wav'] for r in json.loads(
    (PARENT / 'tail_repair_manifest.json').read_text(encoding='utf-8'))['repairs']}

CORNERS = [0, 600, 800, 1000, 1200, 1500, 2000]

for label, pick in (('RAW cut (worst case)', lambda g, n: raw_path(g, n)),
                    ('CURRENT delivered', lambda g, n: repaired.get('S_PKM_%s' % n)
                     or raw_path(g, n))):
    print('\n================ %s ================' % label)
    print('%-16s %6s %8s %9s %9s %9s' % ('clip', 'corner', 'bed resid', 'min margin', 'frames', 'silent%'))
    rows = []
    for group, items in (('reload', RELOAD), ('charge', CHARGE)):
        for name, a, b in items:
            sig = np.asarray(sf.read(pick(group, name))[0], dtype=np.float64)
            for corner in CORNERS:
                f = hp(sig, corner)
                P = spec(f)
                sel = freqs >= corner if corner else np.ones_like(freqs, bool)
                bed_band = float(bed_psd[group][sel].sum())
                frame_power = P[sel].sum(axis=0)
                peak = float(np.max(np.abs(f)))
                live = frame_power > 10 ** (SILENT_DB / 10)
                m = 10 * np.log10(frame_power[live] / (bed_band + 1e-30) + 1e-30)
                row = {'clip': name, 'corner_hz': corner,
                       'bed_residual_dbfs': round(10 * np.log10(bed_band + 1e-30), 1),
                       'residual_below_peak_db': round(
                           10 * np.log10(bed_band + 1e-30) - 20 * np.log10(peak + 1e-30), 1),
                       'peak': round(peak, 5),
                       'min_margin_db': round(float(m.min()), 1) if live.any() else None,
                       'pct_frames_silent': round(100 * float((~live).mean()), 1)}
                rows.append(row)
                if corner in (0, 1200, 1500):
                    print('%-16s %6d %8.1f %9s %9d %9.1f'
                          % (name, corner, row['bed_residual_dbfs'],
                             row['min_margin_db'], len(m), row['pct_frames_silent']))
    (HERE / ('_diag_hp_%s.json' % ('raw' if 'RAW' in label else 'cur'))).write_text(
        json.dumps(rows, indent=2), encoding='utf-8')

    print('\n  residual music below each clip peak (dB) -- bigger is safer')
    print('  %-16s %s' % ('clip', ' '.join('%7d' % c for c in CORNERS)))
    for group, items in (('reload', RELOAD), ('charge', CHARGE)):
        for name, a, b in items:
            vals = [r['residual_below_peak_db'] for r in rows if r['clip'] == name]
            print('  %-16s %s' % (name, ' '.join('%7.1f' % v for v in vals)))