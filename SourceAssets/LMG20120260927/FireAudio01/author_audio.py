"""Author four 201 fire one-shots from the user-selected video soundtrack.

Waveform measurements drive editorial cuts and level matching only. This does
not play audio or run a gameplay test. Original AAC and float masters remain.
"""
from pathlib import Path
import hashlib
import json
import subprocess

import imageio_ffmpeg
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'Source/BV11xwQz5EHS.m4a'
URL = 'https://www.bilibili.com/video/BV11xwQz5EHS/'
# Last transient of separate bursts, each followed by a complete quiet gap.
# These starts precede the steep pressure rise, not the maximum sample.
STARTS = [25.8794, 26.7542, 27.5860, 29.8868]
DURATION = .285


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    for folder in ['Audio', 'Masters']:
        (ROOT / folder).mkdir(exist_ok=True)
    decoded = ROOT / 'reference_23_55_float.wav'
    subprocess.run([
        imageio_ffmpeg.get_ffmpeg_exe(), '-v', 'error', '-y', '-i', str(SOURCE),
        '-ss', '23', '-t', '32', '-vn', '-c:a', 'pcm_f32le', str(decoded),
    ], check=True)
    reference, rate = sf.read(decoded, always_2d=True, dtype='float64')
    # Filter the continuous recording before slicing to avoid filter-start clicks.
    filtered = sosfilt(butter(2, 65, 'highpass', fs=rate, output='sos'), reference, axis=0)
    filtered = sosfilt(butter(2, 14500, 'lowpass', fs=rate, output='sos'), filtered, axis=0)
    length = round(DURATION * rate)
    t = np.arange(length) / rate
    # Above the source floor, preserve the pressure wave and early reflections.
    # Beyond 170 ms the remainder approaches ambience; smoothly taper it away.
    tail = np.clip((t - .170) / (DURATION - .170), 0, 1)
    envelope = np.cos(tail * np.pi / 2) ** 2
    fade_in = round(.00035 * rate)
    envelope[:fade_in] *= np.linspace(0, 1, fade_in)
    records, clips = [], []
    for index, start in enumerate(STARTS, 1):
        first = round((start - 23) * rate)
        raw = reference[first:first + length].copy()
        y = filtered[first:first + length].copy() * envelope[:, None]
        name = f'S_LMG201_Fire_{index:02d}'
        master = ROOT / 'Masters' / (name + '_float.wav')
        sf.write(master, raw, rate, subtype='FLOAT')
        energy = float(np.sqrt(np.mean(y[:round(.150 * rate)] ** 2)))
        clips.append(y)
        records.append({
            'name': name, 'source_start': 23 + first / rate,
            'source_end': 23 + (first + length) / rate,
            'source_samples_in_23s_decode': [first, first + length],
            'duration': length / rate, 'sample_rate': rate,
            'channels': reference.shape[1], 'early_rms_before_match': energy,
            'master': str(master.relative_to(ROOT)),
        })
    target = float(np.median([r['early_rms_before_match'] for r in records]))
    for i, row in enumerate(records):
        gain = float(np.clip(target / row['early_rms_before_match'], 10 ** (-1.5 / 20), 10 ** (1.5 / 20)))
        clips[i] *= gain
        row['variation_gain'] = gain
    # One common gain preserves matched relative levels and stereo balance.
    ceiling = 10 ** (-1 / 20)
    common_gain = ceiling / max(float(np.max(np.abs(y))) for y in clips)
    for y, row in zip(clips, records):
        y *= common_gain
        path = ROOT / 'Audio' / (row['name'] + '.wav')
        sf.write(path, y, rate, subtype='PCM_16')
        row.update({
            'file': str(path.relative_to(ROOT)), 'sha256': digest(path),
            'common_gain': common_gain, 'sample_peak': float(np.max(np.abs(y))),
            'full_clip_rms': float(np.sqrt(np.mean(y ** 2))),
        })
    metadata = json.loads((ROOT / 'Source/BV11xwQz5EHS.info.json').read_text(encoding='utf-8'))
    provenance = {
        'source_url': URL, 'source_bvid': 'BV11xwQz5EHS',
        'source_title': metadata['title'], 'source_uploader': metadata.get('uploader'),
        'source_audio': str(SOURCE.relative_to(ROOT)), 'source_sha256': digest(SOURCE),
        'source_format': 'Bilibili 30280 AAC; native 44100 Hz stereo',
        'request': 'Extract and process firing after 25 seconds for the 201 light machine gun.',
        'selection': 'Four final shots from separate bursts after 25 s; each cut ends before the next burst.',
        'rights': 'User-directed local extraction. Third-party rights retained; public redistribution license not established.',
        'authenticity': 'Mixed uploaded video soundtrack, not isolated original recording stems.',
        'processing': {
            'highpass_hz': 65, 'lowpass_hz': 14500, 'filter_order': 2,
            'fade_in_ms': .35, 'tail_taper_start_ms': 170,
            'tail_end_ms': 285, 'level_match': '150 ms RMS median, gain limited to +/-1.5 dB',
            'sample_peak_ceiling_dbfs': -1,
            'pitch_or_time_shift': False, 'added_sound_layers': False,
            'runtime_format': 'Native-rate stereo PCM16',
        },
        'runtime': {
            'asset_root': '/Game/Weapons/LMG201/FireAudio01', 'variant_count': len(records),
            'max_voices': 6, 'adjacent_repeats': False, 'pitch_multiplier': 1,
            'suppressed_branch': 'Preserve existing suppressor sound',
        },
        'cues': records, 'auditioned': False, 'game_tested': False,
    }
    (ROOT / 'provenance.json').write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding='utf-8')
    print('LMG201_FIRE_AUDIO_AUTHORED', len(records), rate, 'Hz', length, 'samples each')


if __name__ == '__main__':
    main()
