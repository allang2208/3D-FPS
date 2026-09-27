"""Preserve the reference video's original speed, pitch, stereo and tails."""
from pathlib import Path
import hashlib
import json
import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'BowVideoAudio20260926/reference_32_49.wav'
OUT = HERE / 'Wav'
OUT.mkdir(exist_ok=True)
x, rate = sf.read(SOURCE, always_2d=True)
# One shared gain for the pair: do not boost quiet draw/background to the same
# peak as the much stronger release transient. Keep the source stereo mix.
recipes = [
    ('S_BowVideoDirect_Draw', 37.45, 38.15, .003, .010),
    ('S_BowVideoDirect_Release', 36.772, 37.205, .001, .015),
]
cuts = [x[round((start-32)*rate):round((end-32)*rate)].copy()
        for _, start, end, _, _ in recipes]
shared_gain = min(1., 10**(-1./20.) / max(float(np.abs(cut).max()) for cut in cuts))
outputs = []
for (name, start, end, fade_in, fade_out), cut in zip(recipes, cuts):
    # Only soften the edit boundaries; no denoising, EQ, mono fold-down,
    # stretching, pitch shifting, synthesis or time-domain reconstruction.
    n_in, n_out = round(fade_in*rate), round(fade_out*rate)
    cut[:n_in] *= np.linspace(0., 1., n_in)[:, None]
    cut[-n_out:] *= np.linspace(1., 0., n_out)[:, None]
    cut *= shared_gain
    target = OUT / (name+'.wav')
    sf.write(target, cut, rate, subtype='PCM_16')
    outputs.append({'asset': name, 'video_cut_seconds': [start, end],
                    'seconds': len(cut)/rate, 'rate': rate, 'channels': cut.shape[1],
                    'shared_gain': shared_gain, 'speed': 1., 'fade_seconds': [fade_in, fade_out],
                    'sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
(HERE/'audio-manifest.json').write_text(json.dumps({
    'source_url': 'https://www.bilibili.com/video/BV1jGdDBkEkc/',
    'source_file': str(SOURCE), 'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'method': 'Direct stereo excerpts with short boundary fades only. Original speed, pitch and relative level retained.',
    'rights': 'User-requested local video excerpts; no asset redistribution license supplied.',
    'auditioned': False, 'runtime_tested': False, 'outputs': outputs,
}, ensure_ascii=False, indent=2), encoding='utf-8')
print('BOW_VIDEO_DIRECT_AUTHORED '+json.dumps(outputs))
