"""Diagnostic only: per-clip audible wind, and where each clip's window sits.

Key question: which delivered one-shots can a listener actually hear wind in?
Wind is audible when its own band level approaches the mechanism level.  For
each clip this reports the wind band level, the mechanism level, and the margin
between them, plus how much the clip's own leveling gain raised the wind.

Writes only into `_wind/`.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

HERE = Path(__file__).resolve().parent
OUT = HERE / '_wind'
SR = 48000
NPERSEG, NOVERLAP = 2048, 1792
WIND_BAND = (250, 1000)      # where this recording's bed is loudest after the 200 Hz HPF
MECH_BAND = (1000, 6000)     # mechanism is broadband bright; wind is mid/low weighted

STAGES = [
    ('Open', .305, .555, .52), ('Eject', 1.800, 2.230, .46),
    ('Retrieve', 2.780, 3.030, .20), ('Insert', 3.190, 3.760, .42),
    ('Release', 3.895, 4.040, .33), ('Withdraw', 4.080, 4.385, .18),
    ('Close', 4.940, 5.420, .58),
]
QUIET_SPANS = [(.65, 1.65), (2.28, 2.65), (4.47, 4.82), (5.60, 6.35)]

raw, sr = sf.read(HERE / 'Analysis/715-reloading-decoded.wav', always_2d=True)
mono = raw.mean(axis=1)
sos = signal.butter(3, 200, fs=SR, btype='highpass', output='sos')
clean = signal.sosfiltfilt(sos, mono, axis=0)


def band(x, lo, hi):
    s = signal.butter(3, [lo, hi], fs=SR, btype='bandpass', output='sos')
    return signal.sosfiltfilt(s, x, axis=0)


def dbfs(v):
    return round(float(20 * np.log10(np.sqrt(np.mean(np.asarray(v) ** 2)) + 1e-12)), 2)


# reference: the wind bed measured over the four spans the original pass used
wind_samples = np.concatenate([clean[round(a * SR):round(b * SR)] for a, b in QUIET_SPANS])
wind_ref_db = dbfs(band(wind_samples, *WIND_BAND))

rows = []
for name, a, b, target_peak in STAGES:
    seg = clean[round(a * SR):round(b * SR)]
    w = band(seg, *WIND_BAND)
    m = band(seg, *MECH_BAND)
    # 25 ms sliding windows so the mechanism's own gaps are what we measure
    n = int(.025 * SR)
    hop = int(.005 * SR)
    wind_env = np.array([dbfs(w[i:i + n]) for i in range(0, max(1, len(w) - n), hop)])
    mech_env = np.array([dbfs(m[i:i + n]) for i in range(0, max(1, len(m) - n), hop)])
    delivered, _ = sf.read(HERE / ('Waves/S_DW715_Loader_%s.wav' % name))
    delivered = np.asarray(delivered)
    gain_db = 20 * np.log10(target_peak / max(float(np.max(np.abs(seg))), 1e-12))
    mech_peak_db = float(20 * np.log10(np.max(np.abs(m)) + 1e-12))
    rows.append({
        'clip': name,
        'span_s': [a, b],
        'wind_band_rms_dbfs': dbfs(w),
        'wind_vs_bed_db': round(dbfs(w) - wind_ref_db, 1),
        'mech_band_peak_dbfs': round(mech_peak_db, 1),
        'wind_vs_mech_peak_db': round(dbfs(w) - mech_peak_db, 1),
        'wind_env_max_dbfs': round(float(np.max(wind_env)), 1),
        'mech_env_max_dbfs': round(float(np.max(mech_env)), 1),
        'wind_to_mech_worst_case_db': round(float(np.max(wind_env) - np.max(mech_env)), 1),
        'leveling_gain_db': round(gain_db, 2),
        'delivered_peak': round(float(np.max(np.abs(delivered))), 3),
        'delivered_rms_dbfs': dbfs(delivered),
    })

print('wind bed reference (quiet spans, 250-1000 Hz): %+.1f dBFS' % wind_ref_db)
print()
print('%-9s%22s%22s%14s%10s%10s' % ('clip', 'wind band', 'mech band', 'wind vs mech', 'gain', 'delivered'))
print('%-9s%10s%12s%11s%11s%14s%10s%10s'
      % ('', 'rms dB', 'vs bed dB', 'peak dB', '20log dB', 'worst dB', 'dB', 'rms dB'))
for r in rows:
    print('%-9s%10.1f%12.1f%11.1f%11.1f%14.1f%10.2f%10.1f'
          % (r['clip'], r['wind_band_rms_dbfs'], r['wind_vs_bed_db'],
             r['mech_band_peak_dbfs'], r['wind_vs_mech_peak_db'],
             r['wind_to_mech_worst_case_db'], r['leveling_gain_db'], r['delivered_rms_dbfs']))

print()
print('ranked by how exposed the wind is inside the clip (worst case, higher = more audible):')
for r in sorted(rows, key=lambda x: -x['wind_to_mech_worst_case_db']):
    print('   %-9s %+6.1f dB   (wind rms %+.1f, mechanism peak %+.1f)'
          % (r['clip'], r['wind_to_mech_worst_case_db'], r['wind_band_rms_dbfs'],
             r['mech_band_peak_dbfs']))

(OUT / 'wind_audible.json').write_text(
    json.dumps({'wind_bed_ref_dbfs': wind_ref_db, 'wind_band_hz': WIND_BAND,
                'mech_band_hz': MECH_BAND, 'rows': rows}, indent=2), encoding='utf-8')