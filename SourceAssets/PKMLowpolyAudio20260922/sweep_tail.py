"""Sweep tail decay parameters and measure against the AKM reference profile.

The first authored build fixed the padding but its tail decayed ~14 dB in the
50 ms after the blast, so by the 92.3 ms fire interval the tail was gone and each
shot still stood alone. This script evaluates candidate decay timescales against
the AKM reference's own RMS profile, so the choice is measured rather than guessed.
Writes candidates to a scratch folder and prints the comparison; it does not touch
S_PKM_Fire.wav.
"""
from pathlib import Path
import wave
import struct
import math

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'S_PKM_Fire.raw.wav'
SCRATCH = HERE / 'tail-candidates'
SCRATCH.mkdir(exist_ok=True)

FIRE_INTERVAL = 0.092308
ATTACK_TAIL_GUARD = 0.008
DECAY_TARGET = 0.130
END_FADE = 0.005
REFERENCE_PEAK = 0.6025

BANDS = ((220.0, 1400.0), (600.0, 4200.0), (1800.0, 7000.0))


def rms_envelope(samples, rate, win_ms=2.5):
    win = max(1, int(rate * win_ms / 1000.0))
    return [math.sqrt(float(np.mean(samples[i:i + win] ** 2)))
            for i in range(0, len(samples) // win * win, win)]


def dbfs(value):
    return 20 * math.log10(max(value, 1e-9))


def measure(path):
    with wave.open(str(path), 'rb') as handle:
        rate = handle.getframerate()
        frames = handle.readframes(handle.getnframes())
    values = np.array(struct.unpack('<%dh' % (len(frames) // 2), frames), dtype=np.float64) / 32768.0
    env = rms_envelope(values, rate)
    peak = float(np.max(np.abs(values)))
    rms = math.sqrt(float(np.mean(values ** 2)))
    # Level 92.3 ms in (start of the next shot): how much of the tail survives.
    at_next = int(FIRE_INTERVAL / 0.0025)
    tail_db = dbfs(env[at_next]) if at_next < len(env) else -180.0
    # Decay slope across the first 50 ms of tail.
    return dict(peak=peak, rms=rms, crest=dbfs(peak) - dbfs(rms),
                env=env, tail_at_next_db=tail_db,
                min_window_db=dbfs(min(env)))


x, rate = sf.read(SOURCE, always_2d=True, dtype='float64')
signal = x[:, 0]
env = rms_envelope(signal, rate)
peak_index = int(np.argmax(env))
threshold = env[peak_index] * 0.01
above = np.nonzero(np.array(env) >= threshold)[0]
start = max(0, int(above[0] * rate * 0.0025) - int(0.001 * rate))
end = min(len(signal), int((above[-1] + 1) * rate * 0.0025) + int(ATTACK_TAIL_GUARD * rate))
attack = signal[start:end].copy()
bands = [sosfiltfilt(butter(2, [low, high], btype='bandpass', fs=rate, output='sos'), signal)
         for low, high in BANDS]

print("AKM reference profile:")
akm = measure(HERE.parent / 'AKMVideoAudio20260921' / 'S_AKM_Fire.wav')
print("  peak=%.4f rms=%.5f crest=%.1f dB  level at 92.3 ms=%.1f dB  min window=%.1f dB"
      % (akm['peak'], akm['rms'], akm['crest'], akm['tail_at_next_db'], akm['min_window_db']))
print("  env:", " ".join("%.0f" % dbfs(v) for v in akm['env'][:40]))
print()

print("%-28s %6s %8s %8s %12s %10s" % ("candidate", "peak", "rms", "crest", "level@92ms", "min win"))
results = []
for tau in (0.075, 0.120, 0.180):
    for gain in (0.45, 0.55, 0.70):
        total = int(DECAY_TARGET * rate)
        tail_length = total - len(attack)
        decay_time = np.arange(tail_length) / rate
        tail = np.zeros(tail_length)
        for band, (low, high) in zip(bands, BANDS):
            tail += band[start:start + tail_length] * np.exp(-decay_time / tau)
        y = np.concatenate([attack, tail * gain])
        y *= REFERENCE_PEAK / np.max(np.abs(y))
        fade = int(END_FADE * rate)
        y[-fade:] *= np.linspace(1.0, 0.0, fade)
        name = "tau%03d_gain%02d" % (int(tau * 1000), int(gain * 100))
        path = SCRATCH / (name + '.wav')
        sf.write(path, y, rate, subtype='PCM_16')
        m = measure(path)
        results.append((name, tau, gain, m))
        print("%-28s %6.4f %8.5f %8.1f %12.1f %10.1f"
              % (name, m['peak'], m['rms'], m['crest'], m['tail_at_next_db'], m['min_window_db']))

print()
print("Envelopes (2.5 ms windows, dBFS), AKM first for reference:")
print("  %-16s %s" % ("AKM", " ".join("%.0f" % dbfs(v) for v in akm['env'][:52])))
for name, tau, gain, m in results:
    print("  %-16s %s" % (name, " ".join("%.0f" % dbfs(v) for v in m['env'][:52])))
