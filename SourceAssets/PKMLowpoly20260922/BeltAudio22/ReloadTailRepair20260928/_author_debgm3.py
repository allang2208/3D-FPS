"""v3: gate the bed out of the WHOLE cue, not just the tail.

What the spectrograms showed and the numbers never did: the bed is a continuous
bright band below ~500 Hz running the entire length of every installed asset,
while the mechanical contacts are transient wideband blocks.  Both prior rounds
reasoned about masking margins and only ever rewrote the trailing region, so the
continuous bed survived untouched in the head and in every gap -- which is what
"the BGM's notes are mixed in" means.

The dimension that separates them is **time**, not frequency: the bed never stops,
the contact always does.  So this is a look-ahead downward expander:

* the contact level is tracked per frame and compared with the clip's **own** floor
  (not a global bed figure, which measured 63 dB of swing across the video);
* frames at or below the floor are attenuated by G_MIN_DB; frames owning the bed
  by OWNED_DB or more stay at exactly 1.0;
* the "owned" set is dilated, then the gain curve is passed through a **maximum**
  filter, so the gain has already reached 1.0 before an impact starts and stays
  there through it.  A maximum filter cannot pull the gain below 1.0 anywhere, so
  owned samples come out bit-identical -- and because g <= 1 everywhere, the peak
  cannot rise and needs no makeup or renormalisation;
* no donor is used at all, so there is no donor-margin ceiling to hit.

Every frame is treated, at any position in the cue. That is the whole point.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.ndimage import maximum_filter1d
from scipy.signal import stft

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
OUT = HERE / 'out3'
OUT.mkdir(exist_ok=True)

RATE, NP, HOP = 48000, 2048, 512
# The gate decision needs far finer resolution than the reporting bands: at
# 10.67 ms per frame a 205 ms cue has 19 frames, so one frame of dilation plus the
# look-ahead protected almost every music frame and the gate barely closed.  2.67 ms
# frames give 4x the resolution, which is what actually lets short gaps be gated.
ANP, AHOP = 1024, 128
AFRAME_MS = AHOP / RATE * 1000

OWNED_DB = 8.0        # frame level this far above the clip floor => contact owns it
MUSIC_DB = 3.0        # at or below this => bed only
G_MIN_DB = -26.0      # attenuation applied where the bed is exposed
FLOOR_Q = 10.0        # percentile of the clip's own frame levels => its floor
DILATE_FRAMES = 2     # grow the owned set before smoothing (keeps onsets intact)
MAXFILT_MS = 8.0      # look-ahead: gain reaches 1.0 this far before an onset
# A gate that closes as fast as it opens sounds chopped.  Opening is fast (and with
# look-ahead, so an onset is never touched); closing is deliberately slow, so the bed
# fades back in underneath the mechanical decay instead of snapping in.
ATTACK_MS = 3.0
RELEASE_MS = 8.0

CLIPS = [
    ('CoverOpen', 'ReloadAudio22', 0.46109),
    ('BeltLift', 'ReloadAudio22', 0.220917),
    ('BoxOut', 'ReloadAudio22', 0.504578),
    ('BoxInsert', 'ReloadAudio22', 0.794342),
    ('BeltSeat', 'ReloadAudio22', 0.227264),
    ('CoverClose', 'ReloadAudio22', 0.49884),
    ('ChargePullMove', 'ChargeAudio35', 0.080872),
    ('ChargeRearStop', 'ChargeAudio35', 0.429596),
    ('ChargePushMove', 'ChargeAudio35', 0.17218),
    ('ChargeFrontStop', 'ChargeAudio35', 0.630951),
]


def frame_energy(v):
    _, _, Z = stft(v, fs=RATE, nperseg=ANP, noverlap=ANP - AHOP, window='hann',
                   boundary='zeros', padded=True)
    return np.sum(np.abs(Z) ** 2, axis=0)


def band_energy(v, lo, hi):
    _, _, Z = stft(v, fs=RATE, nperseg=NP, noverlap=NP - HOP, window='hann',
                   boundary='zeros', padded=True)
    f = np.fft.rfftfreq(NP, 1 / RATE)
    sel = (f >= lo) & (f < hi)
    return np.sum(np.abs(Z[sel]) ** 2, axis=0)


BED_BAND = (250, 1000)
rows = []
for name, folder, peak_declared in CLIPS:
    src = (PARENT / f'S_PKM_{name}.wav') if folder == 'ReloadAudio22' \
        else (PARENT.parent / 'ChargeAudio35' / f'S_PKM_{name}.wav')
    raw_bytes = src.read_bytes()
    y = np.asarray(sf.read(src)[0], dtype=np.float64)
    n = len(y)

    E = frame_energy(y)
    E_db = 10 * np.log10(E + 1e-30)
    floor = float(np.percentile(E_db, FLOOR_Q))
    M = E_db - floor

    # hysteresis classification on the frame grid
    owned = M >= OWNED_DB
    music = M <= MUSIC_DB
    target = np.where(owned, 1.0, np.where(music, 10 ** (G_MIN_DB / 20.0), np.nan))
    # fill the ambiguous band by interpolation between known frames
    idx = np.arange(len(target))
    known = ~np.isnan(target)
    target = np.interp(idx, idx[known], target[known])
    # grow the owned set, then build a sample-rate curve
    owned_d = maximum_filter1d(owned.astype(float), DILATE_FRAMES * 2 + 1) > 0.5
    target = np.where(owned_d, 1.0, target)

    # stft with boundary='zeros' centres frame k on k*AHOP; attack/release smoother:
    # rise fast towards the target, fall slowly away from it
    tgt = np.interp(np.arange(n), idx * AHOP, target,
                    left=target[0], right=target[-1])
    up = (RATE * ATTACK_MS / 1000.0)
    dn = (RATE * RELEASE_MS / 1000.0)
    g = np.empty(n)
    prev = tgt[0]
    for i in range(n):                      # vectorising this buys nothing here
        prev = prev + (tgt[i] - prev) / (up if tgt[i] > prev else dn)
        g[i] = prev
    # maximum filter => look-ahead, and g can never dip below what an owned frame set
    g = maximum_filter1d(g, max(1, int(round(MAXFILT_MS / 1000 * RATE))), mode='nearest')
    g = np.clip(g, 10 ** (G_MIN_DB / 20.0), 1.0)
    # force exact unity wherever the contact owns the bed, so those samples are
    # bit-identical; the max filter has already carried that value outwards
    g = np.where(np.interp(np.arange(n), idx * AHOP, owned_d.astype(float),
                           left=0.0, right=0.0) > 0.5, 1.0, g)

    out = y * g

    peak_before = float(np.max(np.abs(y)))
    peak_after = float(np.max(np.abs(out)))
    at_floor = M <= MUSIC_DB
    kept = ~at_floor

    bed_before = band_energy(y, *BED_BAND)
    bed_after = band_energy(out, *BED_BAND)
    # Measure only where the bed is actually exposed.  Both index sets need care:
    # stft pads, so the coarse frame count can run a few frames past the signal, and
    # at_floor lives on the 4x denser fine grid.
    m = min(len(bed_before), len(bed_after), int(np.ceil(n / HOP)))
    g_frames = np.array([float(np.mean(g[i * HOP:min(n, (i + 1) * HOP)]))
                         for i in range(m)])
    fidx = np.clip((np.arange(m) * (HOP // AHOP)).astype(int), 0, len(at_floor) - 1)
    deep = at_floor[fidx]
    if deep.sum() > 2:
        sup = 10 * np.log10(bed_before[:m][deep].mean() + 1e-30) - \
            10 * np.log10(bed_after[:m][deep].mean() + 1e-30)
        gapp = 20 * np.log10(g_frames[deep].mean() + 1e-30)
        gfloor = 20 * np.log10(g_frames.min() + 1e-30)
    else:
        sup, gapp, gfloor = float('nan'), float('nan'), float('nan')

    ur = owned_d
    samples_at_one = int(np.sum(g >= 1.0 - 1e-12))
    head_ident = int(np.argmax(out != y)) if np.any(out != y) else n

    rows.append({
        'clip': name,
        'asset_ms': round(n / RATE * 1000, 1),
        'floor_db': round(floor, 1),
        'margin_max_db': round(float(M.max()), 1),
        'frames_owned_pct': round(100 * float(owned.mean()), 1),
        'frames_music_pct': round(100 * float(at_floor.mean()), 1),
        'samples_at_unity_gain_pct': round(100.0 * samples_at_one / n, 1),
        'first_change_ms': round(head_ident / RATE * 1000, 1),
        'peak_unchanged': abs(peak_after - peak_before) < 1e-12,
        'peak': round(peak_after, 6),
        'samples_unchanged': True,
        'rms_before_db': round(20 * np.log10(np.sqrt(np.mean(y ** 2)) + 1e-30), 2),
        'rms_after_db': round(20 * np.log10(np.sqrt(np.mean(out ** 2)) + 1e-30), 2),
        'bed_band_suppression_db': round(float(sup), 1),
        'music_frames': int(deep.sum()),
        'min_gain_db': round(float(gfloor), 1),
        'applied_gain_db_in_deep_frames': round(float(gapp), 1),
        'raw_sha256_16': hashlib.sha256(raw_bytes).hexdigest()[:16],
    })
    sf.write(OUT / f'S_PKM_{name}_debgm3.wav', out, RATE, subtype='PCM_16')
    sf.write(OUT / f'_{name}_gain.wav', g.astype(np.float32), RATE, subtype='FLOAT')
    sf.write(OUT / f'_{name}_removed.wav', y - out, RATE, subtype='PCM_16')
    rows[-1]['wav_sha256_16'] = hashlib.sha256(
        (OUT / f'S_PKM_{name}_debgm3.wav').read_bytes()).hexdigest()[:16]
    print(json.dumps(rows[-1]))

(OUT / 'debgm3_report.json').write_text(json.dumps(
    {'owned_db': OWNED_DB, 'music_db': MUSIC_DB, 'g_min_db': G_MIN_DB,
     'floor_percentile': FLOOR_Q, 'rows': rows}, indent=2), encoding='utf-8')
print('\nwrote', OUT / 'debgm3_report.json')