"""Diagnostic only: pin down the music bed.

  1. high-resolution harmonic structure of the bed in a quiet stretch
  2. does the bed repeat (music loop)?  -> self-similarity of the bed envelope
  3. side-by-side level of bed vs contact in the two suspect windows
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import stft, butter, sosfiltfilt

HERE = Path(__file__).resolve().parent
RATE = 48000
x, rate = sf.read(HERE / 'reference_audio.wav')
mono = x if x.ndim == 1 else x.mean(axis=1)

# ---- 1. bed harmonic detail on a very long window in the quiet gap --------
seg = mono[round(16.20 * RATE):round(17.60 * RATE)]
f, t, Z = stft(seg, fs=RATE, nperseg=32768, noverlap=16384, window='hann')
P = np.mean(np.abs(Z) ** 2, axis=1)
db = 10 * np.log10(P + 1e-20)
sel = (f >= 50) & (f <= 2000)
fs_, db_ = f[sel], db[sel]
top = np.argsort(db_)[-18:][::-1]
print('strongest bed partials (Hz, dB):',
      [(round(float(fs_[i]), 2), round(float(db_[i]), 1)) for i in top])
# harmonic comb fit: try f0 candidates and score energy on the comb
best = None
for f0 in np.arange(30, 260, 0.25):
    idx = np.round(np.arange(f0, 2000, f0) / (RATE / 32768)).astype(int)
    idx = idx[idx < len(db)]
    score = float(np.mean(db[idx]))
    if best is None or score > best[1]:
        best = (float(f0), score)
print('best harmonic comb f0=%.2f Hz mean-dB=%.1f' % best)

# ---- 2. bed envelope and self-similarity ---------------------------------
sos = butter(4, 250, fs=RATE, btype='highpass', output='sos')
hp = sosfiltfilt(sos, mono)
step = int(0.01 * RATE)
env = np.sqrt(np.convolve(hp ** 2, np.ones(step) / step, mode='same'))[::step]
env = np.log10(env + 1e-9)
# normalise
env = (env - env.mean()) / (env.std() + 1e-12)
n = len(env)
ac = np.correlate(env, env, mode='full')[n - 1:]
ac /= ac[0]
print('autocorrelation of bed envelope, peaks (lag_s, r):')
pk = [i for i in range(int(0.3 * 100), len(ac) - 1)
      if ac[i] > ac[i - 1] and ac[i] >= ac[i + 1] and ac[i] > 0.25]
print([(round(i / 100, 2), round(float(ac[i]), 3)) for i in pk[:20]])

# ---- 3. bed vs contact level in the suspect windows ----------------------
def level_profile(a, b, label):
    lo, hi = a - 0.20, b + 0.20
    s = mono[round(lo * RATE):round(hi * RATE)]
    hp_s = sosfiltfilt(sos, s)
    step = int(0.002 * RATE)
    frames = [(round(lo + i / RATE, 3),
               round(float(np.sqrt(np.mean(hp_s[i:i + step] ** 2))), 5))
              for i in range(0, len(hp_s) - step, step)]
    return {'label': label, 'hf_envelope_2ms': frames}


prof = [level_profile(10.825, 11.340, 'CoverOpen'),
        level_profile(15.865, 16.100, 'CoverClose')]
(HERE / '_diag_bed.json').write_text(json.dumps(
    {'harmonics': [[round(float(fs_[i]), 2), round(float(db_[i]), 1)] for i in top],
     'best_comb': best,
     'autocorr_peaks': [(round(i / 100, 2), round(float(ac[i]), 3)) for i in pk[:20]],
     'profiles': prof}, indent=2), encoding='utf-8')
print('wrote _diag_bed.json')