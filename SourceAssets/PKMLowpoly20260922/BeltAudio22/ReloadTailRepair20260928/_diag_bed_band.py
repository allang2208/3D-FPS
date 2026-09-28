"""Two questions the previous rounds never asked.

1. Where is the bed's energy, really?  The 2026-09-25 partial list stopped at
   1031 Hz, and both rounds assumed the bed was broadband enough that filtering
   could not separate it.  But the DW715 precedent in the skill
   (`ue5-weapon-workflow/references/weapon-audio.md`) was solved exactly that
   way: the wind sat inside the passband, and raising the highpass from 200 Hz
   to 800 Hz took it down 17.8 dB while leaving the mechanical peak untouched.
   So measure the bed's spectrum over the *whole* band before assuming.

2. For a highpass at corner `f`, what is the masking margin in the passband
   [f, Nyquist]?  If the bed lives low and the mechanical transient is
   broadband, there is a corner above which every frame of every cut is clean --
   which would remove the music everywhere (head lead-in included) without
   rebuilding anything, and without the 12.5 dB ceiling a donor rebuild has.

Measured on the **raw cuts** (fully bed-contaminated), so the answer is a worst
case rather than a property of the already-partly-repaired deliveries.
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
OWNED = 6.0

RELOAD = [('CoverOpen', 10.825, 11.340), ('BeltLift', 11.745, 12.185),
          ('BoxOut', 12.420, 12.900), ('BoxInsert', 14.245, 14.470),
          ('BeltSeat', 15.230, 15.435), ('CoverClose', 15.865, 16.100)]
CHARGE = [('ChargePullMove', 24.180, 24.710), ('ChargeRearStop', 24.710, 24.905),
          ('ChargePushMove', 24.905, 25.010), ('ChargeFrontStop', 25.010, 25.225)]
BED_WIN = {'reload': [(1.10, 3.25), (3.90, 5.00), (6.10, 7.25), (7.65, 8.75), (9.05, 10.00)],
           'charge': [(16.00, 16.50), (16.50, 17.00), (17.00, 17.50)]}

x, _ = sf.read(PARENT / 'reference_audio.wav')
mono = x if x.ndim == 1 else x.mean(axis=1)


def spec(sig):
    _, _, Z = stft(sig, fs=RATE, nperseg=NP, noverlap=NP - HOP, window='hann',
                   boundary='zeros', padded=True)
    return np.abs(Z) ** 2


freqs = np.fft.rfftfreq(NP, 1 / RATE)

# ---- 1. where does the bed live? -------------------------------------------------
print('=== bed spectrum (long-term, from the clean windows) ===')
bed_psd = {}
for group, wins in BED_WIN.items():
    P = np.mean([spec(mono[round(a * RATE):round(b * RATE)]).mean(axis=1) for a, b in wins], axis=0)
    bed_psd[group] = P
    total = P.sum()
    print('\n%s group  (total %.1f dBFS)' % (group, 10 * np.log10(total + 1e-30)))
    for lo, hi in [(20, 60), (60, 120), (120, 250), (250, 500), (500, 1000),
                   (1000, 2000), (2000, 4000), (4000, 8000), (8000, 20000)]:
        sel = (freqs >= lo) & (freqs < hi)
        share = 100 * P[sel].sum() / total
        print('   %5d-%5d Hz : %5.1f %% of bed energy   (bed level here %6.1f dB)'
              % (lo, hi, share, 10 * np.log10(P[sel].sum() + 1e-30)))


def raw_path(group, name):
    if group == 'reload':
        return PARENT / f'S_PKM_{name}.wav'
    return ROOT / 'ChargeAudio35' / f'S_PKM_{name}.wav'


# ---- 2. masking margin vs highpass corner ---------------------------------------
CORNERS = [0, 100, 200, 400, 600, 800, 1000, 1200, 1500, 2000, 3000]
print('\n=== passband masking margin (raw cuts): min over all frames of all clips ===')
print('%-8s %10s %10s %10s' % ('corner', 'min margin', 'pct>=6dB', 'worst clip'))
table = []
for corner in CORNERS:
    worst, worst_name, allm, tot, ok = 1e9, '', 0, 0, 0
    for group, items in (('reload', RELOAD), ('charge', CHARGE)):
        P_bed = bed_psd[group]
        for name, a, b in items:
            sig = np.asarray(sf.read(raw_path(group, name))[0], dtype=np.float64)
            if corner:
                sig = sosfilt(butter(4, corner, fs=RATE, btype='highpass', output='sos'), sig)
            P = spec(sig)
            sel = freqs >= corner if corner else np.ones_like(freqs, bool)
            bed_band = P_bed[sel].sum()
            m = 10 * np.log10(P[sel].sum(axis=0) / (bed_band + 1e-30) + 1e-30)
            allm += 1
            tot += len(m)
            ok += int((m >= OWNED).sum())
            if m.min() < worst:
                worst, worst_name = float(m.min()), name
    table.append({'corner_hz': corner, 'min_margin_db': round(worst, 1),
                  'pct_frames_owned': round(100 * ok / tot, 1), 'worst_clip': worst_name})
    print('%-8d %10.1f %10.1f%% %10s' % (corner, worst, 100 * ok / tot, worst_name))

# ---- 3. what a highpass costs the mechanical impact ------------------------------
print('\n=== what each corner costs the impact (raw cuts, per clip) ===')
cost = []
for group, items in (('reload', RELOAD), ('charge', CHARGE)):
    for name, a, b in items:
        sig = np.asarray(sf.read(raw_path(group, name))[0], dtype=np.float64)
        row = {'clip': name}
        for corner in (0, 800, 1200, 1500, 2000):
            f = sig if not corner else sosfilt(
                butter(4, corner, fs=RATE, btype='highpass', output='sos'), sig)
            row['peak_%d' % corner] = round(float(np.max(np.abs(f))), 5)
            row['rms_%d' % corner] = round(float(10 * np.log10(np.mean(f ** 2) + 1e-30)), 1)
        row['peak_loss_1200_db'] = round(20 * np.log10(row['peak_1200'] / row['peak_0'] + 1e-30), 1)
        row['peak_loss_2000_db'] = round(20 * np.log10(row['peak_2000'] / row['peak_0'] + 1e-30), 1)
        cost.append(row)
        print('  %-16s peak %8.5f -> %8.5f @1200Hz (%+5.1f dB) -> %8.5f @2000Hz (%+5.1f dB)'
              % (name, row['peak_0'], row['peak_1200'], row['peak_loss_1200_db'],
                 row['peak_2000'], row['peak_loss_2000_db']))

(HERE / '_diag_bed_band.json').write_text(json.dumps(
    {'bed_bands': {g: [round(float(v), 1) for v in
                       [10 * np.log10(bed_psd[g][(freqs >= lo) & (freqs < hi)].sum() + 1e-30)
                        for lo, hi in [(20, 60), (60, 120), (120, 250), (250, 500), (500, 1000),
                                       (1000, 2000), (2000, 4000), (4000, 8000), (8000, 20000)]]]
                   for g in bed_psd},
     'corner_table': table, 'impact_cost': cost}, indent=2), encoding='utf-8')