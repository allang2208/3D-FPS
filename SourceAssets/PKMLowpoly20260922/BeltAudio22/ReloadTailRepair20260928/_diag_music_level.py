"""Does the music ever get LOUD around a cue window?

The user's report is specific: it is a *brief excerpt* of the video's BGM that got
into the reload.  Every margin computed so far used one **global** bed level
(`BED_WIN`, a 70th percentile per frequency bin over five scattered windows).
If the music swells, or simply sits higher near some cue than that global figure,
then those margins were measured against too low a floor and the "contact-owned"
frames they green-lit are really music.

So: measure the bed's *local* level from the video itself, per cue, over a +-2 s
neighbourhood, and compare it with the global estimate the margins used.  Also
report how far the bed's own envelope swings, so a swell cannot hide in an
average.  Levels are quoted in the delivered asset's dBFS (video level + the
chain's own gain) so they can be read against the asset's peak directly.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt, stft

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
RATE, NP, HOP = 48000, 2048, 512

GAIN = {'reload': -1.9473, 'charge': -0.22140514287644383}
BED_WIN = {
    'reload': [(1.10, 3.25), (3.90, 5.00), (6.10, 7.25), (7.65, 8.75), (9.05, 10.00)],
    'charge': [(16.00, 16.50), (16.50, 17.00), (17.00, 17.50)],
}
# name, video window, group, asset peak dBFS (measured on the delivered file)
CUES = [
    ('CoverOpen', 10.825, 11.340, 'reload', 0.46109),
    ('BeltLift', 11.745, 12.185, 'reload', 0.220917),
    ('BoxOut', 12.420, 12.900, 'reload', 0.504578),
    ('BoxInsert', 14.245, 14.470, 'reload', 0.794342),
    ('BeltSeat', 15.230, 15.435, 'reload', 0.227264),
    ('CoverClose', 15.865, 16.100, 'reload', 0.49884),
    ('ChargePullMove', 24.180, 24.710, 'charge', 0.080872),
    ('ChargeRearStop', 24.710, 24.905, 'charge', 0.429596),
    ('ChargePushMove', 24.905, 25.010, 'charge', 0.17218),
    ('ChargeFrontStop', 25.010, 25.225, 'charge', 0.630951),
]

x, _ = sf.read(PARENT / 'reference_audio.wav')
mono = x if x.ndim == 1 else x.mean(axis=1)
mono = sosfiltfilt(butter(2, 80, fs=RATE, btype='highpass', output='sos'), mono)


def frame_db(sig):
    _, _, Z = stft(sig, fs=RATE, nperseg=NP, noverlap=NP - HOP, window='hann',
                   boundary='zeros', padded=True)
    return 10 * np.log10(np.sum(np.abs(Z) ** 2, axis=0) + 1e-30)


# band-limited (250-1000 Hz) envelope, which is where the bed lives
def band_env(sig):
    _, _, Z = stft(sig, fs=RATE, nperseg=NP, noverlap=NP - HOP, window='hann',
                   boundary='zeros', padded=True)
    f = np.fft.rfftfreq(NP, 1 / RATE)
    sel = (f >= 250) & (f < 1000)
    return 10 * np.log10(np.sum(np.abs(Z[sel]) ** 2, axis=0) + 1e-30)


env = band_env(mono)
t = np.arange(len(env)) * HOP / RATE

print('=== the bed\'s own envelope across the whole 51.57 s video (250-1000 Hz) ===')
print('  median %.1f dB   p10 %.1f   p90 %.1f   min %.1f   max %.1f   swing %.1f dB'
      % (np.median(env), np.percentile(env, 10), np.percentile(env, 90),
         env.min(), env.max(), env.max() - env.min()))

rows = []
print('\n=== per cue: local bed level vs the global figure the margins used ===')
print('%-16s %8s %8s %8s %8s %8s %9s' %
      ('cue', 'global', 'local25', 'local50', 'localMAX', 'assetPk', 'MAX-pk'))
for name, a, b, group, pk in CUES:
    g = GAIN[group]
    glob = float(np.median(frame_db(mono[round(BED_WIN[group][0][0] * RATE):
                                        round(BED_WIN[group][0][1] * RATE)])))
    near = (t >= a - 2.0) & (t <= b + 2.0)
    e = env[near]
    l25, l50, lmax = np.percentile(e, 25), np.median(e), e.max()
    pk_db = 20 * np.log10(pk)
    rows.append({'cue': name, 'global_bed_db': round(glob + g, 1),
                 'local_bed_p25_db': round(l25 + g, 1),
                 'local_bed_median_db': round(l50 + g, 1),
                 'local_bed_max_db': round(lmax + g, 1),
                 'asset_peak_db': round(pk_db, 1),
                 'local_max_vs_peak_db': round(lmax + g - pk_db, 1),
                 'global_understates_by_db': round(l50 - glob, 1)})
    print('%-16s %8.1f %8.1f %8.1f %8.1f %8.1f %9.1f' %
          (name, glob + g, l25 + g, l50 + g, lmax + g, pk_db, lmax + g - pk_db))

print('\n=== where the video\'s music is loudest, and what is playing then ===')
order = np.argsort(env)[::-1]
seen, tops = [], []
for i in order:
    if any(abs(t[i] - s) < 1.0 for s in seen):
        continue
    seen.append(t[i])
    hit = [c[0] for c in CUES if c[1] - 0.1 <= t[i] <= c[2] + 0.1]
    tops.append((round(float(t[i]), 2), round(float(env[i] + GAIN['reload']), 1), hit))
    if len(tops) == 8:
        break
for sec, db, hit in tops:
    print('  t=%6.2f s  %7.1f dB   %s' % (sec, db, ('in cue %s' % hit[0]) if hit else '(no cue)'))

(HERE / 'out2' / 'music_level_report.json').write_text(
    json.dumps({'whole_video_env': {'median': round(float(np.median(env)), 1),
                                    'p90': round(float(np.percentile(env, 90)), 1),
                                    'max': round(float(env.max()), 1)},
                'rows': rows, 'loudest_moments': tops}, indent=2), encoding='utf-8')
print('\nwrote out2/music_level_report.json')