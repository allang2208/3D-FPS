"""Second-generation de-BGM authoring: stop emulating the bed.

Why the first attempt failed, from reading it back and re-measuring:

1. **The rebuild was colour-matched to the bed** (`timbre_reference()` returns the
   bed windows) and then **envelope-matched to the bed** (`oenv/cenv` forces the
   tail to the original tail's level, which *is* the bed's level).  So the
   "music-free" tail was a resynthesis of the music bed -- its spectrum, its
   level, its slow envelope -- from clean material.  Spectrally and dynamically
   that still reads as the bed, which is why the user still hears BGM.
2. **Only the tail was treated.**  A cut out of a continuous bed carries music
   over its whole length; the masking margin is below 6 dB for 23-74 % of each
   cue's frames, not just at the end.

The corrected recipe:

* the tail is **not** shaped to the bed.  It keeps the donor's own mechanical
  colour and gets a **synthetic decay that falls to a floor well below the bed**,
  because in a recording without music the tail decays away -- it does not sit at
  a constant level.  The splice still starts at the old tail's level so there is
  no jump;
* the **highpass is applied to the replacement material, not to the asset**
  (the DW715 lesson, `skills/ue5-weapon-workflow/references/weapon-audio.md`).
  The bed is a low-mid hum -- 78 % of its energy in 250-1000 Hz for the reload
  cuts, 90 % for the charge cuts, tonal partials at 340/504/680 Hz -- so
  filtering the donor removes most of the bed *it* carries.  Applying the same
  filter to the asset was measured and rejected: ChargePullMove loses 5.4 dB of
  peak and 8.1 dB of RMS, because that cue's energy is almost all below 1 kHz.
  Filtering only the donor gets the benefit with none of that damage;
* every contact is rebuilt from the **raw cut**, uniformly, so the kept region is
  the untouched original recording and the covers stop using the old recipe.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.ndimage import uniform_filter1d
from scipy.signal import butter, sosfilt, sosfiltfilt, stft

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
ROOT = PARENT.parent
OUT = HERE / 'out2'
OUT.mkdir(exist_ok=True)

RATE, NP, HOP = 48000, 2048, 512
OWNED = 6.0
MIN_REBUILD_MS = 8.0
DONOR_SRC = (20.843, 21.077)     # 234.7 ms, >=12.5 dB (mean 19.7 dB) over the bed
DONOR_HP_HZ = 1000.0             # applied to the donor ONLY
DECAY_FLOOR_DB = -30.0           # where the rebuilt tail lands, vs its own start
DECAY_SHAPE = 0.6                # <1 front-loads the decay, like a real room tail

CLIPS = [
    ('CoverOpen',        'ReloadAudio22', 10.825, 11.340, 'reload', -1.9473),
    ('BeltLift',         'ReloadAudio22', 11.745, 12.185, 'reload', -1.9473),
    ('BoxOut',           'ReloadAudio22', 12.420, 12.900, 'reload', -1.9473),
    ('BoxInsert',        'ReloadAudio22', 14.245, 14.470, 'reload', -1.9473),
    ('BeltSeat',         'ReloadAudio22', 15.230, 15.435, 'reload', -1.9473),
    ('CoverClose',       'ReloadAudio22', 15.865, 16.100, 'reload', -1.9473),
    ('ChargePullMove',   'ChargeAudio35', 24.180, 24.710, 'charge', -0.22140514287644383),
    ('ChargeRearStop',   'ChargeAudio35', 24.710, 24.905, 'charge', -0.22140514287644383),
    ('ChargePushMove',   'ChargeAudio35', 24.905, 25.010, 'charge', -0.22140514287644383),
    ('ChargeFrontStop',  'ChargeAudio35', 25.010, 25.225, 'charge', -0.22140514287644383),
]
BED_WIN = {
    'reload': [(1.10, 3.25), (3.90, 5.00), (6.10, 7.25), (7.65, 8.75), (9.05, 10.00)],
    'charge': [(16.00, 16.50), (16.50, 17.00), (17.00, 17.50)],
}

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


def rms(v):
    return float(np.sqrt(np.mean(v ** 2)))


donor_full = sosfilt(butter(4, DONOR_HP_HZ, fs=RATE, btype='highpass', output='sos'),
                     mono[round(DONOR_SRC[0] * RATE):round(DONOR_SRC[1] * RATE)])

results = []
for name, folder, sa, sb, group, gain in CLIPS:
    raw_path = (PARENT / f'S_PKM_{name}.wav') if folder == 'ReloadAudio22' \
        else (ROOT / 'ChargeAudio35' / f'S_PKM_{name}.wav')
    raw_bytes = raw_path.read_bytes()
    y = np.asarray(sf.read(raw_path)[0], dtype=np.float64)

    margin = frames_db(y) - (bed_db[group] + gain)
    h = len(margin) - 1
    while h >= 0 and margin[h] < OWNED:
        h -= 1
    ho = min((h + 1) * HOP, len(y))
    tail_n = len(y) - ho

    if tail_n / RATE * 1000 < MIN_REBUILD_MS:
        results.append({'clip': name, 'action': 'skipped',
                        'reason': 'exposed tail %.1f ms below %.1f ms'
                                  % (tail_n / RATE * 1000, MIN_REBUILD_MS)})
        print(json.dumps(results[-1]))
        continue
    # ChargePushMove's delivered asset is padded with digital silence after its
    # own content ends, so its trailing region carries no music at all.  Leave it
    # byte-identical rather than fading its last real milliseconds into a zero tail.
    if float(np.max(np.abs(y[ho:]))) < 1e-6:
        results.append({'clip': name, 'action': 'skipped',
                        'reason': 'trailing region is digital silence (no music to remove)',
                        'handover_ms': round(ho / RATE * 1000, 1),
                        'silent_tail_ms': round(tail_n / RATE * 1000, 1)})
        print(json.dumps(results[-1]))
        continue

    prefix, old_tail = y[:ho].copy(), y[ho:].copy()

    # donor slice, mirror-padded only if a tail is longer than the donor window
    if tail_n <= len(donor_full):
        donor = donor_full.copy()
    else:
        donor = np.pad(donor_full, (0, tail_n - len(donor_full)), mode='reflect')
    env = uniform_filter1d(donor ** 2, 256, mode='nearest')
    s0 = max(0, min(int(np.argmax(env)), len(donor) - tail_n))
    tex = donor[s0:s0 + tail_n].copy()

    # start the splice at the old tail's level so nothing jumps, then decay away
    head_ms = max(1, min(int(0.010 * RATE), tail_n // 4))
    want = rms(old_tail[:head_ms])
    have = rms(tex[:head_ms])
    if have > 0:
        tex *= want / have
    t = np.linspace(0.0, 1.0, tail_n) ** DECAY_SHAPE
    new_tail = tex * (10 ** (DECAY_FLOOR_DB * t / 20.0))

    # never add energy relative to what is replaced
    r_old, r_new = rms(old_tail), rms(new_tail)
    if r_new > r_old:
        new_tail *= r_old / r_new

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

    peak_before = float(np.max(np.abs(y)))
    peak_after = float(np.max(np.abs(out)))
    if peak_after > peak_before:
        out *= peak_before / peak_after
        peak_after = float(np.max(np.abs(out)))

    # how far below the bed does the rebuilt tail now sit?
    bed_asset = bed_db[group] + gain
    tail_power = np.mean(new_tail ** 2)
    results.append({
        'clip': name, 'action': 'rebuilt',
        'asset_ms': round(len(y) / RATE * 1000, 1),
        'handover_sample': int(ho),
        'crossfade_samples': int(xf),
        'handover_ms': round(ho / RATE * 1000, 1),
        'rebuilt_ms': round(tail_n / RATE * 1000, 1),
        'bed_asset_db': round(bed_asset, 1),
        'old_tail_rms_db': round(20 * np.log10(rms(old_tail) + 1e-30), 2),
        'new_tail_rms_db': round(20 * np.log10(rms(new_tail) + 1e-30), 2),
        'new_tail_rms_vs_bed_db': round(10 * np.log10(tail_power + 1e-30) - bed_asset, 1),
        'old_tail_rms_vs_bed_db': round(10 * np.log10(np.mean(old_tail ** 2) + 1e-30) - bed_asset, 1),
        'tail_end_vs_start_db': round(
            10 * np.log10(np.mean(new_tail[-max(1, tail_n // 10):] ** 2) + 1e-30)
            - 10 * np.log10(np.mean(new_tail[:max(1, tail_n // 10)] ** 2) + 1e-30), 1),
        'peak_unchanged': abs(peak_after - peak_before) < 1e-6,
        'peak': round(peak_after, 6),
        'samples_unchanged': len(out) == len(y),
        'kept_head_min_margin_db': round(float(margin[:h + 1].min()), 1) if h >= 0 else None,
        'raw_sha256_16': hashlib.sha256(raw_bytes).hexdigest()[:16],
    })
    sf.write(OUT / f'S_PKM_{name}_debgm2.wav', out, RATE, subtype='PCM_16')
    sf.write(OUT / f'_{name}_tail_OLD.wav', old_tail, RATE, subtype='PCM_16')
    sf.write(OUT / f'_{name}_tail_NEW.wav', new_tail, RATE, subtype='PCM_16')
    sf.write(OUT / f'_{name}_difference.wav', out - y, RATE, subtype='PCM_16')
    results[-1]['wav_sha256_16'] = hashlib.sha256(
        (OUT / f'S_PKM_{name}_debgm2.wav').read_bytes()).hexdigest()[:16]
    print(json.dumps(results[-1]))

(OUT / 'debgm2_report.json').write_text(json.dumps(
    {'bed_db': bed_db, 'donor': DONOR_SRC, 'donor_hp_hz': DONOR_HP_HZ,
     'decay_floor_db': DECAY_FLOOR_DB, 'rows': results}, indent=2), encoding='utf-8')
print('\nwrote', OUT / 'debgm2_report.json')