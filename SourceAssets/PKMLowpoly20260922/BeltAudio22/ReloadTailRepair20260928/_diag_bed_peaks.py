"""Is a highpass actually enough? Two things decide it.

1. Where are the bed's *tonal* partials above 1 kHz?  The 2026-09-25 list stopped
   at 1031 Hz and may simply have been the analysis range.  A highpass only
   removes the recognizable music if every partial sits below the corner, so
   measure prominence all the way to 8 kHz.

2. What does each corner cost?  Report residual bed, peak loss and RMS loss per
   clip so the trade is explicit.

Also settles ChargePushMove's "digital silence" claim in the time domain, since
that skip reason quoted a 245.3 ms handover for what is actually a 340 ms asset.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt, stft

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
ROOT = PARENT.parent
RATE, NP, HOP = 48000, 4096, 1024

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

print('=== 1. bed partials (prominence vs a 1/3-octave local floor) ===')
bed_psd, partials = {}, {}
for group, wins in BED_WIN.items():
    # average over each window's own frames first: the windows are different
    # lengths, so the per-window spectra are ragged and cannot be stacked
    # power-average within each window first: windows have different lengths, so
    # their spectra have different frame counts and cannot be stacked directly
    per_window = []
    for a, b in wins:
        _, _, Z = stft(mono[round(a * RATE):round(b * RATE)], fs=RATE, nperseg=NP,
                       noverlap=NP - HOP, window='hann', boundary='zeros', padded=True)
        per_window.append((np.abs(Z) ** 2).mean(axis=1))
    P = np.mean(per_window, axis=0)
    bed_psd[group] = P
    ratio = 2 ** (1 / 3)
    floor = np.array([P[(freqs >= f / ratio) & (freqs < f * ratio)].mean()
                      for f in np.maximum(freqs, 1.0)])
    prom = 10 * np.log10(P / (floor + 1e-30) + 1e-30)
    pk = [(round(float(freqs[i]), 1), round(float(prom[i]), 1))
          for i in range(2, len(freqs) - 1)
          if prom[i] > 6 and prom[i] >= prom[i - 1] and prom[i] > prom[i + 1]
          and 40 < freqs[i] < 8000]
    pk.sort(key=lambda t: -t[1])
    partials[group] = pk[:40]
    print('\n%s: %d prominent partials, strongest first' % (group, len(pk)))
    for f, p in pk[:22]:
        print('    %8.1f Hz   +%4.1f dB over local floor' % (f, p))
    above = [f for f, p in pk if f > 1200]
    print('  partials above 1200 Hz: %d %s' % (len(above), [round(f) for f in above[:12]]))

repaired = {r['asset_name']: PARENT / r['wav'] for r in json.loads(
    (PARENT / 'tail_repair_manifest.json').read_text(encoding='utf-8'))['repairs']}


def path_for(group, name):
    return repaired.get('S_PKM_%s' % name) or (
        (PARENT / f'S_PKM_{name}.wav') if group == 'reload'
        else (ROOT / 'ChargeAudio35' / f'S_PKM_{name}.wav'))


print('\n=== 2. cost of each corner (repaired assets where they exist) ===')
print('%-16s %6s %9s %9s %9s' % ('clip', 'corner', 'peak dB', 'rms dB', 'bed resid'))
cost_rows = []
for corner in (0, 600, 800, 1000, 1200, 1500, 2000):
    for group, items in (('reload', RELOAD), ('charge', CHARGE)):
        for name, a, b in items:
            sig = np.asarray(sf.read(path_for(group, name))[0], dtype=np.float64)
            f = sig if not corner else sosfilt(
                butter(4, corner, fs=RATE, btype='highpass', output='sos'), sig)
            sel = freqs >= corner if corner else np.ones_like(freqs, bool)
            resid = 10 * np.log10(bed_psd[group][sel].sum() + 1e-30)
            cost_rows.append({
                'clip': name, 'corner': corner,
                'peak_db': round(20 * np.log10(float(np.max(np.abs(f))) + 1e-30), 1),
                'rms_db': round(10 * np.log10(float(np.mean(f ** 2)) + 1e-30), 1),
                'bed_resid_db': round(float(resid), 1)})
            if corner in (0, 1000, 1200):
                print('%-16s %6d %9.1f %9.1f %9.1f' % (name, corner, cost_rows[-1]['peak_db'],
                                                       cost_rows[-1]['rms_db'], resid))

print('\n  delta vs corner 0 (negative = the filter took energy away)')
print('  %-16s %s' % ('clip', ' '.join('%16d' % c for c in (600, 800, 1000, 1200, 1500, 2000))))
for group, items in (('reload', RELOAD), ('charge', CHARGE)):
    for name, a, b in items:
        base = next(r for r in cost_rows if r['clip'] == name and r['corner'] == 0)
        line = []
        for c in (600, 800, 1000, 1200, 1500, 2000):
            r = next(r for r in cost_rows if r['clip'] == name and r['corner'] == c)
            line.append('%6.1f/%5.1f' % (r['peak_db'] - base['peak_db'], r['rms_db'] - base['rms_db']))
        print('  %-16s %s' % (name, ' '.join(line)))

print('\n=== 3. ChargePushMove: is the trailing region really digital silence? ===')
sig = np.asarray(sf.read(path_for('charge', 'ChargePushMove'))[0], dtype=np.float64)
t = np.arange(len(sig)) / RATE * 1000
nz = np.abs(sig) > 0
print('  length %.1f ms; first nonzero at %.1f ms; last nonzero at %.1f ms'
      % (len(sig) / RATE * 1000, t[nz][0] if nz.any() else -1, t[nz][-1] if nz.any() else -1))
for a, b in [(0, 90), (90, 130), (130, 182), (182, 235), (235, 331), (331, 340)]:
    seg = sig[round(a * RATE / 1000):round(b * RATE / 1000)]
    print('    %3d-%3d ms : peak %.6f  rms %.1f dBFS  %s'
          % (a, b, np.max(np.abs(seg)), 10 * np.log10(np.mean(seg ** 2) + 1e-30),
             'ALL ZERO' if not np.any(seg) else ''))
(HERE / '_diag_bed_peaks.json').write_text(json.dumps(
    {'cost': cost_rows, 'partials': partials,
     'partials_above_1200': {g: [f for f, p in v if f > 1200] for g, v in partials.items()}},
    indent=2), encoding='utf-8')