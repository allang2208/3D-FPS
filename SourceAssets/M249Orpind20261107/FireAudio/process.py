"""Build four time-aligned one-shots from the supplied M249 recording."""
import hashlib
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

folder = Path(__file__).resolve().parent
source = Path("D:/FPS3D/资产/音效/M249.mp3")
samples, rate = sf.read(source, always_2d=True)
amplitude = np.abs(samples).max(axis=1)
onset = np.flatnonzero(amplitude > 10 ** (-35 / 20))[0]
start = max(0, onset - round(0.002 * rate))
last = np.flatnonzero(amplitude > 10 ** (-56 / 20))[-1]
end = min(len(samples), last + 1 + round(0.012 * rate))
base = sosfilt(butter(2, 30, "highpass", fs=rate, output="sos"), samples[start:end], axis=0)
for duration, edge in ((0.001, "in"), (0.012, "out")):
    ramp = np.linspace(0, 1, round(duration * rate))[:, None]
    if edge == "in":
        base[:len(ramp)] *= ramp
    else:
        base[-len(ramp):] *= ramp[::-1]

body = sosfilt(butter(2, [180, 850], "bandpass", fs=rate, output="sos"), base, axis=0)
presence = sosfilt(butter(2, [1800, 5800], "bandpass", fs=rate, output="sos"), base, axis=0)
files = []
for i, (low_db, high_db) in enumerate(((0, 0), (.65, -.5), (-.5, .65), (.3, .45)), 1):
    wave = base + np.expm1(np.log(10) * low_db / 20) * body + np.expm1(np.log(10) * high_db / 20) * presence
    wave *= 10 ** (-1.6 / 20) / np.abs(wave).max()
    name = f"S_M249_Fire_{i:02}.wav"
    sf.write(folder / name, wave, rate, subtype="PCM_16")
    files.append(name)
recipe = dict(source=str(source), sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
              rate=rate, channels=samples.shape[1], start_sample=int(start), end_sample=int(end),
              duration=(end - start) / rate, files=files)
(folder / "source.json").write_text(json.dumps(recipe, ensure_ascii=False, indent=2), encoding="utf8")
print("M249 one-shots", len(files), recipe["duration"], rate, "Hz")
