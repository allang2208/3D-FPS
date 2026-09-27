"""Cut and master four stage-specific sounds from the Still North CC0 sources.

Selection is based on source labels and waveform timing, not an audition.
The take-arrow texture is designed from arrow-feather handling, not claimed
to be a recording of pulling an arrow out of a quiver.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly
import imageio_ffmpeg

HERE = Path(__file__).resolve().parent
OUT = HERE / 'Wav'
WORK = HERE / 'Work'
OUT.mkdir(exist_ok=True)
WORK.mkdir(exist_ok=True)
RATE = 48000

# Explicit master-track time ranges make source provenance reproducible.
# Nominal runtime mix multipliers remain in BowWeaponComponent.
RECIPES = [
    ('S_Bow_TakeArrow', 'Arrow Fletching.wav', 16.82, 17.34, .26, -6., 180., .004, .025),
    ('S_Bow_Nock', 'English Longbow Nock Arrow.wav', 3.64, 3.83, .16, -5., 110., .002, .018),
    ('S_Bow_Draw', 'English Longbow Draw.wav', 1.65, 4.19, 1.40, -5., 150., .015, .045),
    ('S_Bow_Release', 'English Longbow Shoot.wav', .087, .56, None, -2., 70., .001, .025),
]
outputs = []
for name, source_name, start, end, seconds, peak_db, hp, fade_in, fade_out in RECIPES:
    source = HERE / 'Original' / source_name
    x, source_rate = sf.read(source, always_2d=True, dtype='float64')
    x = x[round(start * source_rate):round(end * source_rate)].mean(axis=1)
    x = sosfilt(butter(2, hp, 'highpass', fs=source_rate, output='sos'), x)
    # 192 kHz originals are archived untouched; only these short derived files
    # become inline 48 kHz mono assets.
    from math import gcd
    divisor = gcd(source_rate, RATE)
    x = resample_poly(x, RATE // divisor, source_rate // divisor)
    intermediate = WORK / (name + '_cut.wav')
    sf.write(intermediate, x, RATE, subtype='FLOAT')
    if seconds is not None:
        tempo = len(x) / RATE / seconds
        filters = []
        while tempo > 2.:
            filters.append('atempo=2')
            tempo /= 2.
        while tempo < .5:
            filters.append('atempo=0.5')
            tempo /= .5
        filters.append(f'atempo={tempo:.10f}')
        stretched = WORK / (name + '_timed.wav')
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error',
                        '-y', '-i', str(intermediate), '-af', ','.join(filters),
                        '-ar', str(RATE), '-ac', '1', '-c:a', 'pcm_f32le', str(stretched)], check=True)
        x, _ = sf.read(stretched, dtype='float64')
        count = round(seconds * RATE)
        x = np.pad(x, (0, max(0, count - len(x))))[:count]
    count_in = min(len(x), round(fade_in * RATE))
    count_out = min(len(x), round(fade_out * RATE))
    x[:count_in] *= np.linspace(0., 1., count_in)
    x[-count_out:] *= np.linspace(1., 0., count_out)
    gain = 10 ** (peak_db / 20.) / max(float(np.max(np.abs(x))), 1e-12)
    x *= gain
    target = OUT / (name + '.wav')
    sf.write(target, x, RATE, subtype='PCM_16')
    outputs.append(dict(asset=name, source=source_name, cut_seconds=[start, end],
                        seconds=len(x)/RATE, rate=RATE, channels=1, peak_dbfs=peak_db,
                        highpass_hz=hp, fade_seconds=[fade_in, fade_out], gain=gain,
                        sha256=hashlib.sha256(target.read_bytes()).hexdigest()))

(HERE / 'audio-manifest.json').write_text(json.dumps({
    'license': 'CC0-1.0; see sources.json and LICENSE-CC0.txt',
    'authoring': 'Waveform-based cuts, high-pass, pitch-preserving offline time fit, edge fades and peak headroom.',
    'take_arrow_note': 'Designed from Arrow Fletching; not an independently recorded quiver draw.',
    'auditioned': False, 'runtime_tested': False, 'outputs': outputs,
}, indent=2), encoding='utf-8')
print('BOW_AUDIO_AUTHORED ' + json.dumps([{k:r[k] for k in ('asset','seconds')} for r in outputs]))
