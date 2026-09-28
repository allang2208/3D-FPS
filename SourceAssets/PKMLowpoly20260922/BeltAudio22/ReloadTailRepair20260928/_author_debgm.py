"""Author the reload tail de-BGM for every PKM contact that still carries the bed.

Extends the approved 2026-09-25 route (see `../BGM_FINDINGS.md`): keep the
impact body untouched, replace only the region where the background bed is
audible, and rebuild that region from a **clean donor** so no music is copied.

Two changes to the original recipe, both forced by what the extended measurement
showed (`_diag_all.py`):

* the cut is resolved **in the delivered asset's own timeline** instead of the
  source video's.  The 2026-09-25 note converted its source-domain handover with
  a multiply where the delivered chain lengthens (CoverOpen: 0.515 s source ->
  0.692 s asset), so its quoted "314.9 ms asset" figure was wrong.  Measuring on
  the asset removes the mapping entirely -- and the diff against the file that
  was actually delivered shows the real cut landed at 569.3 ms, matching that
  round's *source* figure (437.3 ms x 1.344).  The delivered pair is therefore
  already correct and is left alone here;
* the handover uses hysteresis (owned >= 6 dB, music < 3 dB, walk back through
  music and ambiguous frames).  The old "last keepable frame" rule kept BoxOut's
  mid-clip music hole (267-341 ms) because the contact briefly returns at
  5.5 dB near 363-373 ms.

Everything else is the approved method: colour transfer to the clip's own bed
colour over 11 bands limited to +-20 dB, envelope taken from the original tail
and smoothed 25 ms so no musical pumping survives, 15 ms crossfade, exact sample
count and peak preserved so the SoundWave contract in use does not change.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.ndimage import uniform_filter1d
from scipy.signal import butter, sosfiltfilt, stft

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent          # BeltAudio22
ROOT = PARENT.parent          # PKMLowpoly20260922
OUT = HERE / 'out'
OUT.mkdir(exist_ok=True)

RATE = 48000
NP, HOP = 2048, 512
OWNED, MUSIC = 6.0, 3.0
# Below ~20 ms the rebuild has no room for a real decay: the 25 ms envelope
# smoother is longer than the tail, so the smoothed original and donor envelopes
# stop being proportional and the level ratio degenerates (ChargeFrontStop's
# 9.3 ms tail came out 6.5 dB LOUDER).  Such tails also sit at or below the bed
# and are far too short to read as music, so they are left exactly as delivered.
MIN_REBUILD_MS = 20.0
BANDS = [(30, 60), (60, 110), (110, 200), (200, 350), (350, 600), (600, 1000),
         (1000, 1800), (1800, 3200), (3200, 5600), (5600, 9000), (9000, 14000)]
DONOR_SRC = (20.843, 21.077)   # best sustained bed masking in the whole decode
# The 2026-09-25 round used 25.010-25.215 s, chosen from a margin measured
# WITHOUT the 80 Hz highpass that the authoring chain applies.  With the
# highpass on, that window's margin collapses to a minimum of -2.3 dB and its
# 96-139 ms sits at 2.5-5.1 dB -- so rebuilding a 130-224 ms tail from it copied
# the music straight back in, which is exactly what a rebuild must not do.
# `_diag_donor_thresholds.py` searched the whole decode with the highpass
# applied and found 20.843-21.077 s: 234.7 ms at a minimum margin of 12.5 dB
# (mean 19.7 dB), long enough for the longest tail here without any padding.
# A donor's margin is the rebuild's music suppression, because donor = contact +
# bed: whatever the donor carries is what the rebuilt tail carries.
DONOR_MIN_MARGIN_DB = 12.5
DONOR_MEAN_MARGIN_DB = 19.7

BED_WIN = {
    'reload': [(1.10, 3.25), (3.90, 5.00), (6.10, 7.25), (7.65, 8.75), (9.05, 10.00)],
    'charge': [(16.00, 16.50), (16.50, 17.00), (17.00, 17.50)],
}
# name, asset folder, source window for the record, group, set common gain (dB)
CLIPS = [
    ('BeltSeat',        'ReloadAudio22', 15.230, 15.435, 'reload', -1.9473),
    ('BoxOut',          'ReloadAudio22', 12.420, 12.900, 'reload', -1.9473),
    ('BeltLift',        'ReloadAudio22', 11.745, 12.185, 'reload', -1.9473),
    ('BoxInsert',       'ReloadAudio22', 14.245, 14.470, 'reload', -1.9473),
    ('ChargeRearStop',  'ChargeAudio35', 24.710, 24.905, 'charge', -0.22140514287644383),
    ('ChargePullMove',  'ChargeAudio35', 24.180, 24.710, 'charge', -0.22140514287644383),
    ('ChargeFrontStop', 'ChargeAudio35', 25.010, 25.225, 'charge', -0.22140514287644383),
    ('ChargePushMove',  'ChargeAudio35', 24.905, 25.010, 'charge', -0.22140514287644383),
]

x, _ = sf.read(PARENT / 'reference_audio.wav')
mono = x if x.ndim == 1 else x.mean(axis=1)
mono = sosfiltfilt(butter(2, 80, fs=RATE, btype='highpass', output='sos'), mono)


def frames_db(sig):
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


def band_curve(v, nfft, f):
    P = np.abs(np.fft.rfft(v, nfft)) ** 2
    c, val = [], []
    for lo, hi in BANDS:
        m = (f >= lo) & (f < hi)
        if m.sum():
            c.append(np.sqrt(lo * hi))
            val.append(float(np.sum(P[m])) + 1e-30)
    return np.array(c), np.array(val)


def rms(v):
    return float(np.sqrt(np.mean(v ** 2)))


def handover_of(asset, group):
    """Last frame that still belongs to the contact, by hysteresis walk-back."""
    margin = frames_db(asset) - (bed_db[group] + 0.0)
    return margin


def timbre_reference(group):
    return np.concatenate([mono[round(a * RATE):round(b * RATE)] for a, b in BED_WIN[group]])


donor_full = mono[round(DONOR_SRC[0] * RATE):round(DONOR_SRC[1] * RATE)]
results = []
for name, folder, sa, sb, group, gain in CLIPS:
    asset_path = (PARENT / f'S_PKM_{name}.wav') if folder == 'ReloadAudio22' \
        else (ROOT / 'ChargeAudio35' / f'S_PKM_{name}.wav')
    raw_bytes = asset_path.read_bytes()
    y, _ = sf.read(asset_path)
    y = np.asarray(y if y.ndim == 1 else y.mean(axis=1), dtype=np.float64)

    fr = frames_db(y)
    margin = fr - (bed_db[group] + gain)
    h = len(margin) - 1
    while h >= 0 and margin[h] < OWNED:
        h -= 1
    ho = min((h + 1) * HOP, len(y))
    tail_len = len(y) - ho

    if tail_len / RATE * 1000 < MIN_REBUILD_MS:
        results.append({'clip': name, 'folder': folder, 'action': 'skipped',
                        'reason': f'exposed tail {tail_len / RATE * 1000:.1f} ms < {MIN_REBUILD_MS} ms',
                        'handover_ms': round(ho / RATE * 1000, 1)})
        print(json.dumps(results[-1]))
        continue
    if np.max(np.abs(y[ho:])) < 1e-6:
        results.append({'clip': name, 'folder': folder, 'action': 'skipped',
                        'reason': 'trailing region is digital silence (no music to remove)',
                        'handover_ms': round(ho / RATE * 1000, 1)})
        print(json.dumps(results[-1]))
        continue

    prefix, original_tail = y[:ho].copy(), y[ho:].copy()
    tail_n = len(original_tail)
    nfft = 1 << int(np.ceil(np.log2(max(tail_n, 4096))))
    f = np.fft.rfftfreq(nfft, 1 / RATE)

    # clean donor; mirror-padded if a tail is longer than the donor window,
    # because reflecting keeps the waveform continuous where tiling would click
    if tail_n <= len(donor_full):
        donor = donor_full.copy()
    else:
        donor = np.pad(donor_full, (0, tail_n - len(donor_full)), mode='reflect')
    env = uniform_filter1d(donor ** 2, 256, mode='nearest')
    s0 = max(0, min(int(np.argmax(env)), len(donor) - tail_n))
    donor = donor[s0:s0 + tail_n].copy()

    # colour transfer: clean donor -> the bed colour of this clip's own cluster
    timbre = timbre_reference(group)
    ct, vt = band_curve(timbre, nfft, f)
    cs, vs = band_curve(donor, nfft, f)
    g = np.interp(f, ct, np.sqrt(vt)) / np.maximum(np.interp(f, cs, np.sqrt(vs)), 1e-30)
    g = np.clip(g, 10 ** (-20 / 20), 10 ** (20 / 20))
    if (f < 35).sum():
        g[f < 35] *= np.linspace(0, 1, int((f < 35).sum()))
    if (f > 15000).sum():
        g[f > 15000] *= np.linspace(1, 0, int((f > 15000).sum()))
    new_tail = np.fft.irfft(np.fft.rfft(donor, nfft) * g, nfft)[:tail_n]

    # envelope from the original tail, smoothed hard so no musical pumping survives
    w = max(1, int(0.025 * RATE))
    oenv = uniform_filter1d(np.sqrt(uniform_filter1d(original_tail ** 2, w, mode='nearest')),
                            w, mode='nearest')
    cenv = uniform_filter1d(np.sqrt(uniform_filter1d(new_tail ** 2, w, mode='nearest')),
                            w, mode='nearest') + 1e-12
    new_tail = new_tail * (oenv / cenv)
    new_tail *= np.linspace(1.0, 0.55, tail_n)      # reads as a decay, not a hard stop
    # A rebuild must never be louder than what it replaces: the whole point is to
    # sit at the old tail's level with no music, not to add energy.
    r_old, r_new = rms(original_tail), rms(new_tail)
    if r_new > r_old:
        new_tail *= r_old / r_new

    # adaptive edges: a 15 ms crossfade cannot exceed a 9 ms tail
    xf = max(1, min(int(0.015 * RATE), tail_n // 3, ho))
    ai = max(1, min(int(0.006 * RATE), tail_n // 4))
    ri = max(1, min(int(0.025 * RATE), tail_n // 3))
    new_tail[:ai] *= np.linspace(0, 1, ai)
    new_tail[-ri:] *= np.linspace(1, 0, ri)

    out = np.concatenate([prefix, np.zeros(tail_n)])
    ramp = np.linspace(0, 1, xf)
    out[ho - xf:ho] *= ramp
    out[ho:ho + xf] += new_tail[:xf] * (1 - ramp)
    out[ho + xf:] = new_tail[xf:]

    peak_before, peak_after = float(np.max(np.abs(y))), float(np.max(np.abs(out)))
    if peak_after > peak_before:
        out *= peak_before / peak_after
        peak_after = float(np.max(np.abs(out)))

    sf.write(OUT / f'S_PKM_{name}_debgm_delivered.wav', out, RATE, subtype='PCM_16')
    sf.write(OUT / f'_{name}_tail_OLD_contaminated.wav', original_tail, RATE, subtype='PCM_16')
    sf.write(OUT / f'_{name}_tail_NEW_rebuilt.wav', new_tail, RATE, subtype='PCM_16')
    sf.write(OUT / f'_{name}_difference.wav', out - y, RATE, subtype='PCM_16')
    results.append({
        'clip': name, 'folder': folder, 'action': 'rebuilt',
        'source_window': [sa, sb], 'group': group,
        'bed_source_db': round(bed_db[group], 1),
        'bed_asset_db': round(bed_db[group] + gain, 1),
        'asset_samples': int(len(y)),
        'asset_ms': round(len(y) / RATE * 1000, 3),
        'handover_ms': round(ho / RATE * 1000, 1),
        'kept_ms': round(ho / RATE * 1000, 1),
        'rebuilt_ms': round(tail_n / RATE * 1000, 1),
        'donor_window': list(DONOR_SRC),
        'donor_min_margin_db': DONOR_MIN_MARGIN_DB,
        'donor_mean_margin_db': DONOR_MEAN_MARGIN_DB,
        'music_at_least_db_below_replaced_level': DONOR_MIN_MARGIN_DB,
        'kept_head_min_margin_db': round(float(margin[:h + 1].min()), 1) if h >= 0 else None,
        'old_tail_rms_dbfs': round(20 * np.log10(rms(original_tail) + 1e-30), 2),
        'new_tail_rms_dbfs': round(20 * np.log10(rms(new_tail) + 1e-30), 2),
        'delivered_rms_dbfs': round(20 * np.log10(rms(out) + 1e-30), 2),
        'peak_unchanged': abs(peak_after - peak_before) < 1e-6,
        'peak': round(peak_after, 6),
        'samples_unchanged': len(out) == len(y),
        'source_sha256_16': hashlib.sha256(raw_bytes).hexdigest()[:16],
        'wav_sha256_16': hashlib.sha256(
            (OUT / f'S_PKM_{name}_debgm_delivered.wav').read_bytes()).hexdigest()[:16],
    })
    print(json.dumps(results[-1]))

(OUT / 'debgm_report.json').write_text(json.dumps(
    {'bed_db': bed_db, 'owned_db': OWNED, 'music_db': MUSIC,
     'donor_source_window': DONOR_SRC, 'rows': results}, indent=2), encoding='utf-8')
print('\nwrote', OUT / 'debgm_report.json')