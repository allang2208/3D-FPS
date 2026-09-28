"""Author the rebuild: keep the impact, replace only the BGM-contaminated tail.

Method (route 1):
  * everything up to the handover frame is the untouched original impact;
  * the contaminated tail is rebuilt from a **clean donor** -- ChargeRelease,
    the only contact whose whole window sits >= 6 dB above the bed -- not from
    the clip's own contaminated material, so no music can be re-copied;
  * its colour is taken from a **clean timbre reference**: the clip's own quiet
    surround, which is the same room and mechanism but carries no contact;
  * envelope follows the original tail's smoothed decay; butt splice is
    crossfaded 15 ms.

Outputs to `rebuild/`; nothing is installed into Content.
"""
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
import imageio_ffmpeg
from scipy.ndimage import uniform_filter1d
from scipy.signal import butter, sosfiltfilt

HERE = Path(__file__).resolve().parent
OUT = HERE / 'rebuild'
OUT.mkdir(exist_ok=True)
RATE = 48000
FADE_IN_S, FADE_OUT_S, X_FADE_S = 0.006, 0.025, 0.015
BANDS = [(30, 60), (60, 110), (110, 200), (200, 350), (350, 600), (600, 1000),
         (1000, 1800), (1800, 3200), (3200, 5600), (5600, 9000), (9000, 14000)]

x, rate = sf.read(HERE / 'reference_audio.wav')
mono = x if x.ndim == 1 else x.mean(axis=1)
mono = sosfiltfilt(butter(2, 80, fs=RATE, btype='highpass', output='sos'), mono)

DONOR = (25.010, 25.215)          # ChargeRelease: 100 % of frames >= 6 dB over bed
COMMON_GAIN_DB = -1.9473          # author_audio.py common_gain_db, keeps set balance
PLAN = [
    {'name': 'CoverOpen', 'start': 10.825, 'end': 11.340, 'tempo': .72,
     'handover_s': 437.3 / 1000,
     'timbre': (9.05, 10.00)},     # quiet surround, same room, no contact
    {'name': 'CoverClose', 'start': 15.865, 'end': 16.100, 'tempo': 1.0,
     'handover_s': 192.0 / 1000,
     'timbre': (15.10, 15.75)},
]


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


results = []
for p in PLAN:
    a, b = p['start'], p['end']
    seg = mono[round(a * RATE):round(b * RATE)].copy()
    ho = int(round(p['handover_s'] * RATE))
    prefix, original_tail = seg[:ho].copy(), seg[ho:].copy()
    tail_len = len(original_tail)
    nfft = 1 << int(np.ceil(np.log2(max(tail_len, 4096))))
    f = np.fft.rfftfreq(nfft, 1 / RATE)

    # clean donor, sliced to length and longest-energy aligned
    d0, d1 = DONOR
    donor = mono[round(d0 * RATE):round(d1 * RATE)]
    reps = int(np.ceil(tail_len / len(donor)))
    donor = np.tile(donor, reps)
    env = uniform_filter1d(donor ** 2, 256, mode='nearest')
    s0 = max(0, min(int(np.argmax(env)), len(donor) - tail_len))
    donor = donor[s0:s0 + tail_len].copy()

    # colour transfer: clean donor -> clean timbre reference
    t0, t1 = p['timbre']
    timbre = mono[round(t0 * RATE):round(t1 * RATE)]
    ct, vt = band_curve(timbre, nfft, f)
    cs, vs = band_curve(donor, nfft, f)
    gain = np.interp(f, ct, np.sqrt(vt)) / np.maximum(np.interp(f, cs, np.sqrt(vs)), 1e-30)
    gain = np.clip(gain, 10 ** (-20 / 20), 10 ** (20 / 20))
    gain[f < 35] *= np.linspace(0, 1, int((f < 35).sum())) if (f < 35).sum() else 1
    gain[f > 15000] *= np.linspace(1, 0, int((f > 15000).sum())) if (f > 15000).sum() else 1
    new_tail = np.fft.irfft(np.fft.rfft(donor, nfft) * gain, nfft)[:tail_len]

    # envelope from the original tail, smoothed hard so no musical pumping survives
    w = max(1, int(0.025 * RATE))
    oenv = uniform_filter1d(np.sqrt(uniform_filter1d(original_tail ** 2, w, mode='nearest')),
                            w, mode='nearest')
    cenv = uniform_filter1d(np.sqrt(uniform_filter1d(new_tail ** 2, w, mode='nearest')),
                            w, mode='nearest') + 1e-12
    new_tail = new_tail * (oenv / cenv)
    # gentle monotone release so the ending reads as a decay, not a hard stop
    new_tail *= np.linspace(1.0, 0.55, tail_len)

    ai, ri, xf = int(FADE_IN_S * RATE), int(FADE_OUT_S * RATE), int(X_FADE_S * RATE)
    new_tail[:ai] *= np.linspace(0, 1, ai)
    new_tail[-ri:] *= np.linspace(1, 0, ri)

    out = np.concatenate([prefix, np.zeros(tail_len)])
    ramp = np.linspace(0, 1, xf)
    out[ho - xf:ho] *= ramp
    out[ho:ho + xf] += new_tail[:xf] * (1 - ramp)
    out[ho + xf:] = new_tail[xf:]

    # delivered chain
    proc = out
    if p['tempo'] != 1.:
        with tempfile.TemporaryDirectory(prefix='pkm_rb2_') as t_:
            iw, ow = Path(t_) / 'in.wav', Path(t_) / 'out.wav'
            sf.write(iw, proc, RATE, subtype='FLOAT')
            subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-v', 'error',
                            '-i', str(iw), '-af', f"atempo={p['tempo']}",
                            '-c:a', 'pcm_f32le', str(ow)], check=True)
            proc = sf.read(ow)[0]
    proc = np.asarray(proc).copy()
    fa, fr = round(.003 * RATE), round(.025 * RATE)
    proc[:fa] *= np.linspace(0, 1, fa)
    proc[-fr:] *= np.linspace(1, 0, fr)
    # ffmpeg atempo emits a content-dependent number of samples; the game's
    # contact timing uses this asset length, so match the asset in use exactly.
    target = (HERE / f'S_PKM_{p["name"]}.wav')
    if target.exists():
        ref_len = len(sf.read(target)[0])
        if len(proc) > ref_len:
            proc = proc[:ref_len]
    # author_audio.py normalises the whole set with one gain (peak -> -2 dBFS).
    # Same gain here, so the rebuilt pair keeps the set's relative balance and
    # the SoundWave volume already in use stays valid.
    proc = proc * (10 ** (COMMON_GAIN_DB / 20))

    sf.write(OUT / f'S_PKM_{p["name"]}_rebuilt_raw.wav', out, RATE, subtype='PCM_16')
    sf.write(OUT / f'S_PKM_{p["name"]}_rebuilt_delivered.wav', proc, RATE, subtype='PCM_16')
    sf.write(OUT / f'_{p["name"]}_removed_tail.wav', original_tail, RATE, subtype='PCM_16')
    sf.write(OUT / f'_{p["name"]}_new_tail.wav', new_tail, RATE, subtype='PCM_16')

    results.append({
        'clip': p['name'], 'donor': f'ChargeRelease {d0}-{d1} s',
        'timbre_reference': f'{t0}-{t1} s (quiet surround)',
        'handover_ms': round(p['handover_s'] * 1000, 1),
        'kept_impact_ms': round(ho / RATE * 1000, 1),
        'rebuilt_tail_ms': round(tail_len / RATE * 1000, 1),
        'old_tail_rms_dbfs': round(20 * np.log10(rms(original_tail)), 2),
        'new_tail_rms_dbfs': round(20 * np.log10(rms(new_tail)), 2),
        'delivered_rms_dbfs': round(20 * np.log10(rms(proc)), 2),
        'delivered_peak': round(float(np.max(np.abs(proc))), 4),
        'delivered_samples': len(proc),
    })
    print(json.dumps(results[-1]))

(OUT / 'rebuild_report.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
print()
for fp in sorted(OUT.glob('*.wav')):
    print(fp.name, fp.stat().st_size, hashlib.sha256(fp.read_bytes()).hexdigest()[:16])