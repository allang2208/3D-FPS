"""Diagnostic only: where the background bed becomes audible in each played contact.

Criterion (extends the approved 2026-09-25 method in `../_diag_bounds.py`):

* bed reference is measured in the same 80 Hz-HP decode, from quiet windows
  *local* to each cluster -- the reload cluster sits at 10.8-16.1 s, the charge
  cluster at 24.2-25.2 s and the nearest clean stretch is 16.0-17.5 s;
* the margin is measured **on the delivered asset itself**, in asset units, so
  no source->asset tempo mapping is needed:  bed_asset = bed_source + common_gain
  of that set (`audio_manifest.json`);
* a frame is contact-owned at >= 6 dB, music-owned below 3 dB, ambiguous in
  between.  The handover is found by walking back from the end through
  music-owned and ambiguous frames and stopping at the first contact-owned
  frame -- so a mid-clip music hole (BoxOut 267-341 ms) is handed over too,
  which the old "last keepable frame" rule silently kept.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt, stft

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
ROOT = PARENT.parent
RATE = 48000
NP, HOP = 2048, 512

BED_WIN = {
    'reload': [(1.10, 3.25), (3.90, 5.00), (6.10, 7.25), (7.65, 8.75), (9.05, 10.00)],
    'charge': [(16.00, 16.50), (16.50, 17.00), (17.00, 17.50)],
}

# name, asset folder, source window (s), group, set common gain (dB)
CLIPS = [
    ('CoverOpen',       'ReloadAudio22', 10.825, 11.340, 'reload', -1.9473),
    ('BeltLift',        'ReloadAudio22', 11.745, 12.185, 'reload', -1.9473),
    ('BoxOut',          'ReloadAudio22', 12.420, 12.900, 'reload', -1.9473),
    ('BoxInsert',       'ReloadAudio22', 14.245, 14.470, 'reload', -1.9473),
    ('BeltSeat',        'ReloadAudio22', 15.230, 15.435, 'reload', -1.9473),
    ('CoverClose',      'ReloadAudio22', 15.865, 16.100, 'reload', -1.9473),
    ('ChargePullMove',  'ChargeAudio35', 24.180, 24.710, 'charge', -0.22140514287644383),
    ('ChargeRearStop',  'ChargeAudio35', 24.710, 24.905, 'charge', -0.22140514287644383),
    ('ChargePushMove',  'ChargeAudio35', 24.905, 25.010, 'charge', -0.22140514287644383),
    ('ChargeFrontStop', 'ChargeAudio35', 25.010, 25.225, 'charge', -0.22140514287644383),
]

x, rate = sf.read(PARENT / 'reference_audio.wav')
mono = x if x.ndim == 1 else x.mean(axis=1)
mono = sosfiltfilt(butter(2, 80, fs=RATE, btype='highpass', output='sos'), mono)


def frames_of(sig):
    _, _, Z = stft(sig, fs=RATE, nperseg=NP, noverlap=NP - HOP, window='hann',
                   boundary='zeros', padded=True)
    return 10 * np.log10(np.sum(np.abs(Z) ** 2, axis=0) + 1e-30)


bed_db = {}
for group, wins in BED_WIN.items():
    Ps = []
    for a, b in wins:
        _, _, Z = stft(mono[round(a * RATE):round(b * RATE)], fs=RATE, nperseg=NP,
                       noverlap=NP - HOP, window='hann', boundary='zeros', padded=True)
        Ps.append(np.abs(Z) ** 2)
    bed_db[group] = float(10 * np.log10(np.sum(np.percentile(
        np.concatenate(Ps, axis=1), 70, axis=1)) + 1e-30))
    print(f'bed[{group}] = {bed_db[group]:.1f} dB (source units)')

OWNED, MUSIC = 6.0, 3.0
rows = []
for name, folder, a, b, group, gain in CLIPS:
    asset_path = (PARENT / f'S_PKM_{name}.wav') if folder == 'ReloadAudio22' \
        else (ROOT / 'ChargeAudio35' / f'S_PKM_{name}.wav')
    y, r = sf.read(asset_path)
    y = y if y.ndim == 1 else y.mean(axis=1)
    fr = frames_of(y)
    bed_asset = bed_db[group] + gain
    margin = fr - bed_asset
    # hysteresis walk-back from the end
    h = len(margin) - 1
    while h >= 0 and margin[h] < OWNED:
        h -= 1
    handover_frame = h + 1                      # first rebuilt frame
    ho_sample = min(handover_frame * HOP, len(y))
    tail_margin = margin[handover_frame:]
    rows.append({
        'name': name, 'folder': folder, 'group': group,
        'source_window': [a, b],
        'asset_samples': int(len(y)), 'asset_ms': round(len(y) / RATE * 1000, 1),
        'bed_source_db': round(bed_db[group], 1), 'bed_asset_db': round(bed_asset, 1),
        'handover_frame': int(handover_frame),
        'handover_ms': round(ho_sample / RATE * 1000, 1),
        'keep_ms': round(ho_sample / RATE * 1000, 1),
        'rebuild_ms': round((len(y) - ho_sample) / RATE * 1000, 1),
        'tail_min_margin_db': round(float(tail_margin.min()), 1) if len(tail_margin) else None,
        'tail_max_margin_db': round(float(tail_margin.max()), 1) if len(tail_margin) else None,
        'head_min_margin_db': round(float(margin[:handover_frame].min()), 1) if handover_frame else None,
        'margins_db': [round(float(v), 1) for v in margin],
    })
    r_ = {k: v for k, v in rows[-1].items() if k != 'margins_db'}
    print(json.dumps(r_))
    print('   per 10.7 ms frame:',
          [f'{round(i * HOP / RATE * 1000)}:{v}' for i, v in enumerate(rows[-1]['margins_db'])])
    print()

(HERE / '_diag_all.json').write_text(json.dumps(
    {'bed_db': bed_db, 'owned_db': OWNED, 'music_db': MUSIC, 'frames': rows},
    indent=2), encoding='utf-8')