"""Original periodic stereo rain synthesis; requires NumPy, no recordings."""
from pathlib import Path
import wave
import numpy as np

ROOT = Path(__file__).resolve().parents[1] / 'assets/sfx/weather'
RATE, SECONDS = 22050, 24
n = RATE * SECONDS
rng = np.random.default_rng(260906)
freq = np.fft.rfftfreq(n, 1 / RATE)
t = np.arange(n) / RATE

def noise(cutoff):
    spectrum = np.fft.rfft(rng.normal(size=n))
    shape = (freq / (freq + 180)) / np.sqrt(1 + (freq / cutoff) ** 6)
    return np.fft.irfft(spectrum * shape, n=n)

for name, cutoff, rms in [('rain_soft_v2', 1400, .18), ('rain_patter_v2', 2800, .13)]:
    channels = []
    shared = noise(cutoff)
    for channel in range(2):
        signal = .72 * shared + .28 * noise(cutoff)
        if 'patter' in name:
            impulses = np.zeros(n)
            indices = rng.integers(0, n, SECONDS * 95)
            np.add.at(impulses, indices, rng.uniform(.2, 1, len(indices)))
            kernel = np.exp(-np.arange(n) / (RATE * .018))
            envelope = np.fft.irfft(np.fft.rfft(impulses) * np.fft.rfft(kernel), n=n)
            signal *= .2 + envelope
        signal *= .93 + .045 * np.sin(t * 2 * np.pi / 8 + channel * .3) + .025 * np.sin(t * 2 * np.pi / 24)
        signal *= rms / np.sqrt(np.mean(signal ** 2))
        channels.append(signal)
    data = np.stack(channels, axis=1)
    data *= min(1, .92 / np.max(np.abs(data)))
    pcm = np.round(data * 32767).astype('<i2')
    with wave.open(str(ROOT / (name + '.wav')), 'wb') as stream:
        stream.setparams((2, 2, RATE, 0, 'NONE', 'not compressed'))
        stream.writeframes(pcm.tobytes())
    # The seam is a normal adjacent sample in a periodic signal, with no silence/fade gap.
    seam = np.max(np.abs(data[0] - data[-1]))
    typical = np.sqrt(np.mean(np.diff(data, axis=0) ** 2))
    assert seam < typical * 6
    print(name, 'duration', SECONDS, 'peak', round(float(abs(data).max()), 4), 'seam_step/rms_step', round(float(seam / typical), 3))
