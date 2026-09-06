"""Original open-land thunder: filtered stochastic cracks, rolling body, diffuse echoes.

NumPy synthesis only; no third-party recordings. Run from any working directory.
"""
from pathlib import Path
import wave
import numpy as np

ROOT = Path(__file__).resolve().parents[1] / 'assets/sfx/weather'
RATE = 22050
SECONDS = 11
N = RATE * SECONDS
T = np.arange(N) / RATE
F = np.fft.rfftfreq(N, 1 / RATE)

def write(path, samples):
    with wave.open(str(path), 'wb') as stream:
        stream.setparams((2, 2, RATE, 0, 'NONE', 'not compressed'))
        stream.writeframes(np.round(samples * 32767).astype('<i2').tobytes())

def generate(variant):
    rng = np.random.default_rng(202609060 + variant)

    def noise(low, high):
        spectrum = np.fft.rfft(rng.normal(size=N))
        filtered = np.fft.irfft(spectrum * (F / (F + low)) ** 2 /
                                np.sqrt(1 + (F / high) ** 6), n=N)
        return filtered / max(1e-8, np.std(filtered))

    def burst(at, attack, decay):
        age = np.maximum(0, T - at)
        return (1 - np.exp(-age / attack)) * np.exp(-age / decay) * (T >= at)

    # Irregular, rapid micro-cracks merge into a thunder onset rather than a gunshot.
    dry = np.zeros(N)
    for at, gain in [(0, .7), (.038, .42), (.103, .32), (.19, .18)]:
        dry += noise(180, 2600) * burst(at, .003, .035) * gain
    body = noise(28, 420)
    for at, gain, decay in [(0, .68, 1.0), (.22, .42, 1.5), (.63, .3, 1.8),
                            (1.35, .24, 1.65), (2.2, .13, 1.5)]:
        dry += body * burst(at + rng.uniform(0, .07), .035, decay) * gain
    dry *= .86 + .09 * np.sin(T * 8.7 + variant) + .05 * np.sin(T * 17.1)

    # Sparse distant reflections spread into clusters; no short periodic room echo.
    distant = np.fft.irfft(np.fft.rfft(dry) / np.sqrt(1 + (F / 650) ** 6), n=N)
    stereo = np.repeat(dry[:, None], 2, axis=1) * .78
    for ch in range(2):
        for delay, gain in [(.43, .18), (.88, .15), (1.47, .115), (2.25, .08), (3.25, .045)]:
            for _ in range(7):
                offset = int((delay + rng.uniform(-.075, .13)) * RATE)
                stereo[offset:, ch] += distant[:-offset] * gain / 7
        stereo[:, ch] += noise(30, 240) * burst(.25, .35, 2.0) * .075

    stereo *= np.minimum(1, np.maximum(0, SECONDS - T) / 1.2)[:, None]
    stereo[:8] *= np.linspace(0, 1, 8)[:, None]
    stereo *= .88 / np.max(np.abs(stereo))
    assert np.isfinite(stereo).all() and np.max(abs(stereo)) < .9
    assert np.max(abs(stereo[-1])) < .0001
    path = ROOT / f'thunder_wilderness_{variant}.wav'
    write(path, stereo)
    print(path.name, '11s stereo, peak', round(float(abs(stereo).max()), 3),
          'tail RMS', round(float(np.sqrt(np.mean(stereo[-RATE:] ** 2))), 6))
    return stereo

if __name__ == '__main__':
    ROOT.mkdir(parents=True, exist_ok=True)
    for index in range(1, 4):
        generate(index)
