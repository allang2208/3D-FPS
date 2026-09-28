"""Diagnostic only: stereo side-channel content + bed repetition test."""
import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
RATE = 48000
SOURCE = HERE.parent / 'References/PKM_UserReloadReference.mp4'
import imageio_ffmpeg

tmp = Path(tempfile.mkdtemp(prefix='pkm_st_'))
st_path = tmp / 'st.wav'
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-v', 'error', '-i', str(SOURCE),
                '-vn', '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s24le', str(st_path)],
               check=True)
st, rate = sf.read(st_path)
assert rate == RATE and st.ndim == 2
L, R = st[:, 0], st[:, 1]
mid, side = (L + R) / 2, (L - R) / 2
print('decoded stereo', st.shape)


def rms(v):
    return float(np.sqrt(np.mean(v ** 2)))


def band(v, lo, hi):
    from scipy.signal import butter, sosfiltfilt
    return float(np.sqrt(np.mean(sosfiltfilt(
        butter(4, [lo, hi], fs=RATE, btype='bandpass', output='sos'), v) ** 2)))


WINDOWS = [('CoverOpen', 10.825, 11.340), ('CoverClose', 15.865, 16.100),
           ('quiet_16.3_17.3', 16.30, 17.30), ('quiet_1.1_2.1', 1.10, 2.10)]
rows = []
for nm, a, b in WINDOWS:
    sl = slice(round(a * RATE), round(b * RATE))
    m, s = mid[sl], side[sl]
    rows.append({'label': nm,
                 'mid_rms': round(rms(m), 5), 'side_rms': round(rms(s), 5),
                 'side_minus_mid_db': round(20 * np.log10(rms(s) / (rms(m) + 1e-12)), 2),
                 'corr_LR': round(float(np.corrcoef(L[sl], R[sl])[0, 1]), 4),
                 'mid_low_rms': round(band(m, 60, 400), 5),
                 'side_low_rms': round(band(s, 60, 400), 5)})
    print(json.dumps(rows[-1]))

(HERE / '_diag_stereo.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')

# ---------------- repetition test on the decoded stereo mid ----------------
from scipy.signal import butter, sosfiltfilt
sos = butter(4, 250, fs=RATE, btype='highpass', output='sos')
hp = sosfiltfilt(sos, mid)
D = 6
hpd = hp[::D]
rate_d = RATE / D
print(f'correlating at {rate_d:.0f} Hz')


def best_match(a, b):
    p0, p1 = int(a * rate_d), int(b * rate_d)
    probe = hpd[p0:p1].copy()
    probe -= probe.mean()
    n = len(probe)
    ref = np.concatenate([hpd[:max(0, p0 - n)], hpd[p1 + n:]])
    nfft = 1 << int(np.ceil(np.log2(len(ref) + n)))
    F = np.fft.rfft(ref, nfft) * np.conj(np.fft.rfft(probe, nfft))
    cc = np.fft.irfft(F, nfft)[:len(ref) - n]
    e_ref = np.sqrt(np.convolve(ref ** 2, np.ones(n), 'valid')[:len(cc)]) + 1e-12
    ncc = cc / (e_ref * np.linalg.norm(probe))
    order = np.argsort(ncc)[::-1][:5]
    out = []
    for i in order:
        t_abs = i / rate_d if i < p0 - n else (i + 2 * n) / rate_d
        out.append((round(float(t_abs), 3), round(float(ncc[i]), 4)))
    return out


rep = []
for nm, a, b in [('CoverOpen_tail', 11.30, 11.90), ('CoverClose_tail', 16.06, 16.66),
                 ('earlier_bed', 12.95, 13.55), ('later_bed', 24.00, 24.60),
                 ('very_late', 45.0, 45.6)]:
    m = best_match(a, b)
    rep.append({'label': nm, 'probe': [a, b], 'best_matches': m})
    print(json.dumps(rep[-1]))
(HERE / '_diag_repeat.json').write_text(json.dumps(rep, indent=2), encoding='utf-8')