"""Edit short bow cues from the user's video; no game playback or audition."""
from pathlib import Path
from math import ceil
import hashlib
import json
import subprocess
import numpy as np
import soundfile as sf
from scipy.ndimage import gaussian_filter
from scipy.signal import butter, sosfiltfilt, stft, istft
import imageio_ffmpeg

HERE = Path(__file__).resolve().parent
OUT = HERE / 'Wav'
WORK = HERE / 'Work'
OUT.mkdir(exist_ok=True)
WORK.mkdir(exist_ok=True)
RATE = 48000
x, rate = sf.read(HERE / 'reference_32_49.wav', always_2d=True)
if rate != RATE:
    raise RuntimeError('Authoring source must be 48 kHz')
x = x.mean(axis=1)
x = sosfiltfilt(butter(2, 95, 'highpass', fs=RATE, output='sos'), x)
# Estimate a steady background spectrum over the reference, then gently reduce
# it without replacing the video's transient or imposing a hard noise gate.
_, _, z = stft(x, fs=RATE, nperseg=1024, noverlap=768)
mag = np.abs(z)
noise = np.quantile(mag, .20, axis=1, keepdims=True)
gain = np.clip(1. - (1.4 * noise / np.maximum(mag, 1e-10)) ** 2, .10, 1.)
gain = gaussian_filter(gain, sigma=(.65, .65))
_, cleaned = istft(z * gain, fs=RATE, nperseg=1024, noverlap=768)
cleaned = cleaned[:len(x)]

# Video seconds: choose handling/engagement from the quiet pre-draw interval;
# the release ends before the later target-impact transient. The draw keeps
# its build-up and final engagement, fitted offline with pitch preserved.
recipes = [
    ('S_BowVideo_TakeArrow', 35.72, 35.88, .16, -8., .004, .018),
    ('S_BowVideo_Nock', 36.186, 36.286, .10, -6., .002, .015),
    ('S_BowVideo_Draw', 37.45, 38.12, 1.40, -3., .010, .030),
    ('S_BowVideo_Release', 36.772, 36.938, None, -1., .001, .020),
]
outputs = []
for name, start, end, seconds, peak_db, fade_in, fade_out in recipes:
    y = cleaned[round((start - 32) * RATE):round((end - 32) * RATE)].copy()
    cut = WORK / (name + '_cut.wav')
    sf.write(cut, y, RATE, subtype='FLOAT')
    if seconds is not None and abs(len(y)/RATE - seconds) > .005:
        tempo = len(y)/RATE/seconds
        filters = []
        while tempo < .5:
            filters.append('atempo=0.5')
            tempo /= .5
        while tempo > 2.:
            filters.append('atempo=2')
            tempo /= 2.
        filters.append(f'atempo={tempo:.10f}')
        timed = WORK / (name + '_timed.wav')
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error',
                        '-y', '-i', str(cut), '-af', ','.join(filters), '-ar', str(RATE),
                        '-ac', '1', '-c:a', 'pcm_f32le', str(timed)], check=True)
        y, _ = sf.read(timed)
    if seconds is not None:
        n = round(seconds * RATE)
        y = np.pad(y, (0, max(0, n - len(y))))[:n]
    n_in, n_out = round(fade_in * RATE), round(fade_out * RATE)
    y[:n_in] *= np.linspace(0., 1., n_in)
    y[-n_out:] *= np.linspace(1., 0., n_out)
    normalization = 10 ** (peak_db/20.) / max(float(np.max(np.abs(y))), 1e-10)
    y *= normalization
    target = OUT / (name + '.wav')
    sf.write(target, y, RATE, subtype='PCM_16')
    outputs.append({
        'asset': name, 'video_cut_seconds': [start, end], 'seconds': len(y)/RATE,
        'rate': RATE, 'channels': 1, 'peak_dbfs': peak_db,
        'fade_seconds': [fade_in, fade_out], 'normalization': normalization,
        'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
    })
(HERE / 'audio-manifest.json').write_text(json.dumps({
    'source': 'https://www.bilibili.com/video/BV1jGdDBkEkc/',
    'selection': 'Reference-frame stages and waveform transient boundaries; not auditioned.',
    'processing': 'Mono, 95 Hz high-pass, soft spectral background reduction, pitch-preserving draw time fit, fades, peak headroom.',
    'rights': 'User-requested local excerpts; no redistribution license supplied; not CC0.',
    'auditioned': False, 'runtime_tested': False, 'outputs': outputs,
}, ensure_ascii=False, indent=2), encoding='utf-8')
print('BOW_VIDEO_AUDIO_AUTHORED ' + json.dumps([{k:r[k] for k in ('asset','seconds')} for r in outputs]))
