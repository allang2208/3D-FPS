"""Build a looping panting wave; the debuff owns entry/exit fades and duration."""
import json
import subprocess
import wave
from pathlib import Path
import numpy as np

source = Path(__file__).resolve().parent
ffmpeg = Path('C:/Users/allan/AppData/Local/Programs/Python/Python311/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe')
decoded = subprocess.run([
    str(ffmpeg), '-hide_banner', '-loglevel', 'error', '-y',
    '-i', str(source / 'Panting_drewsimko_682882_hq.mp3'),
    '-af', 'highpass=f=70,lowpass=f=11000,loudnorm=I=-22:TP=-3:LRA=7',
    '-ac', '1', '-ar', '48000', '-f', 'f32le', 'pipe:1',
], check=True, stdout=subprocess.PIPE).stdout
samples = np.frombuffer(decoded, dtype='<f4')
rate = 48000
overlap = round(rate * 0.08)
weight = np.linspace(0.0, 1.0, overlap, endpoint=False)
seam = samples[-overlap:] * (1.0 - weight) + samples[:overlap] * weight
# End in the crossfaded opening, then wrap to the next sample of that opening.
# There is no silence padding or periodic fade-out between cycles.
loop = np.concatenate((samples[overlap:-overlap], seam))
pcm = (np.clip(loop, -1.0, 1.0) * 32767).astype('<i2')
with wave.open(str(source / 'S_ExhaustionPanting.wav'), 'wb') as output:
    output.setnchannels(1)
    output.setsampwidth(2)
    output.setframerate(rate)
    output.writeframes(pcm.tobytes())
(source / 'loop-preparation.json').write_text(json.dumps({
    'sample_rate': rate, 'channels': 1, 'duration_seconds': len(loop) / rate,
    'loop_crossfade_seconds': overlap / rate, 'silence_padding': False,
}, indent=2), encoding='utf-8')
