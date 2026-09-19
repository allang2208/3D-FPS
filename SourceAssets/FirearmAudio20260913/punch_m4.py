from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / 'ProcessingDeps'))
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

root = Path(__file__).resolve().parent
source = root.parent / 'M4HK416AudioEmpty20260909/Audio/fire.wav'
x, rate = sf.read(source, always_2d=True)
t = np.arange(len(x)) / rate
# Parallel gentle body EQ retains the original stereo recording and pitch.
body = sosfilt(butter(2, [100, 200], btype='bandpass', fs=rate, output='sos'), x, axis=0)
mud = sosfilt(butter(2, [280, 480], btype='bandpass', fs=rate, output='sos'), x, axis=0)
y = x + .22 * body - .10 * mud
# +2.5 dB initial impact, smoothly back to unity by 45 ms.
attack = 1 + (10 ** (2.5 / 20) - 1) * (1 - np.clip((t - .008) / .037, 0, 1))
# Keep the tail alive; taper to -3.5 dB between 65 and 200 ms.
tail_blend = np.clip((t - .065) / .135, 0, 1)
tail_blend = tail_blend * tail_blend * (3 - 2 * tail_blend)
envelope = attack * (1 + (10 ** (-3.5 / 20) - 1) * tail_blend)
y *= envelope[:, None]
# Linked stereo soft knee on exceptional peaks, leaving low levels unchanged.
peak = np.max(np.abs(y), axis=1)
limited = np.where(peak > .75, .75 + .15 * np.tanh((peak - .75) / .15), peak)
y *= (limited / np.maximum(peak, 1e-12))[:, None]
out = root / 'M4Punch20260914'
out.mkdir(exist_ok=True)
for i, gain in enumerate([1.0, .94, 1.04, .97], 1):
    variation = 1 + (gain - 1) * np.clip((t - .09) / .10, 0, 1)
    sf.write(out / f'S_M4_Original_{i:02d}.wav', y * variation[:, None], rate, subtype='PCM_16')
print('M4 punch audio authored: four stereo variants.')
