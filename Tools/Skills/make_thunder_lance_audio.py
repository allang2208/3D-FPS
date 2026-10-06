"""Thunder Lance audio — original procedural synthesis, no third-party samples.

Discharge: hard broadband crack, dense electrical sizzle, low thunder tail.
Charge: rising crackle bed + swelling hum that resolves into a held plateau.
"""
import json, wave
import numpy as np
from scipy.signal import butter, sosfilt
from pathlib import Path

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/ThunderLanceRay20261005')
for d in ('Audio', 'Records'):
    (ROOT / d).mkdir(parents=True, exist_ok=True)
sr = 48000
rng = np.random.default_rng(6021)

def bp(x, lo, hi):
    return sosfilt(butter(3, [lo, hi], btype='bandpass', fs=sr, output='sos'), x)
def lp(x, f):
    return sosfilt(butter(3, f, btype='lowpass', fs=sr, output='sos'), x)
def hp(x, f):
    return sosfilt(butter(3, f, btype='highpass', fs=sr, output='sos'), x)
def smooth(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)
def save_wav(y, name):
    y = y - y.mean()
    y = y * (.92 / max(.92, float(np.abs(y).max())))
    path = ROOT / 'Audio' / (name + '.wav')
    with wave.open(str(path), 'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(sr)
        f.writeframes((32767 * y).astype('<i2').tobytes())
    (ROOT / 'Records' / (name + '.json')).write_text(json.dumps(
        {'file': str(path), 'duration': round(len(y) / sr, 2), 'sample_rate': sr,
         'provenance': 'Original procedural synthesis; no third-party samples', 'tested': False},
        indent=2), encoding='utf8')
    print('LANCE_AUDIO_SAVED', path)

# ── Discharge: crack -> sizzle -> boom tail ──
dur = 2.2
t = np.arange(int(dur * sr)) / sr
n = rng.normal(0, 1, len(t))
crackle = bp(n, 1800, 9000)
body = bp(n, 200, 1400)
sub = lp(n, 220)
y = np.zeros(len(t))

# Instant crack: three stacked bursts (snap + echo snap + falling tail burst),
# then a low-frequency slam so the attack hits the chest, not just the ears.
for a, amp, dec in ((0.0, 1.15, 210.), (0.015, .7, 150.), (0.034, .5, 110.)):
    age = np.maximum(t - a, 0)
    y += (t >= a) * amp * crackle * np.exp(-age * dec)
    y += (t >= a) * amp * .8 * body * np.exp(-age * (dec * .7))
# Chest slam: saturated low thump decaying in ~90ms.
slam_age = np.maximum(t - .002, 0)
slam = np.exp(-slam_age * 55.) * np.sin(2 * np.pi * (95 * slam_age - 25 * slam_age * slam_age))
y += (t >= .002) * slam * 1.5
# Dense electrical sizzle: impulses arrive fast at first then thin out.
density = np.clip(1 - t / 1.0, 0., 1.) ** 1.5 * .95
impulse = (rng.random(len(t)) < density * .3).astype(float) * rng.normal(0, 1, len(t))
sizzle_env = smooth(t / .012) * (1 - smooth((t - .2) / .95))
y += sizzle_env * bp(impulse, 1400, 8200) * 3.4
y += sizzle_env * crackle * .22
# Launch hum: fast swell, held ~0.55s, released as the beam dies.
hum = smooth(t / .035) * (1 - smooth((t - .62) / .5))
y += hum * (.30 * np.sin(2 * np.pi * (118 * t + 30 * t * t))
            + .14 * np.sin(2 * np.pi * (236 * t + 41 * t * t)))
# Thunder tail: sub boom + rumble noise decaying under everything.
tail = smooth(t / .010) * (1 - smooth((t - .34) / 1.6))
y += tail * (.44 * np.sin(2 * np.pi * (58 * t - 6 * t * t)) + .26 * sub)
# Soft-clip the whole mix: raises RMS/perceived loudness and makes the crack
# read as an explosion instead of clean noise.
y = np.tanh(y * 1.7) * .78
y *= smooth(t / .004) * (1 - smooth((t - 2.05) / .15))
save_wav(y, 'S_ThunderLanceDischarge')

# ── Charge gather: rising crackle bed + swelling hum, held plateau ──
dur = 2.6
t = np.arange(int(dur * sr)) / sr
n = rng.normal(0, 1, len(t))
crackle = bp(n, 2200, 9500)
soft = bp(n, 260, 1600)
y = np.zeros(len(t))
charge = smooth(t / 1.5) * (1 - smooth((t - 2.42) / .16))
# Crackle density ramps with charge: sparse ticks early, dense bed late.
density = (.06 + .80 * smooth(t / 1.8))
impulse = (rng.random(len(t)) < density * .30).astype(float) * rng.normal(0, 1, len(t))
y += charge * bp(impulse, 1600, 8600) * 2.2
y += charge * crackle * .10
# Rising hum: pitch climbs toward the release pitch and holds.
y += charge * (.15 * np.sin(2 * np.pi * (82 * t + 30 * t * t))
               + .06 * np.sin(2 * np.pi * (164 * t + 55 * t * t)))
y += charge * soft * .05
y *= smooth(t / .01) * (1 - smooth((t - 2.5) / .1))
save_wav(y, 'S_ThunderLanceCharge')
print('LANCE_AUDIO_COMPLETE')
