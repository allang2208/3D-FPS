"""Process the supplied one-shot; measurements are authoring inputs, not listening tests."""
from pathlib import Path
import hashlib
import json
import subprocess

import imageio_ffmpeg
import numpy as np
import soundfile as sf
from scipy.signal import butter, lfilter, sosfilt

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
INPUT = Path('D:/FPS3D/资产/音效/M2011viper.mp3')
TARGET = '/Game/Weapons/PitViper2011/Integrated20261002/Audio/S_PitViper2011_Fire'
TONE_EQ = (
    {'kind': 'bell', 'frequency_hz': 400, 'gain_db': -1.5, 'q': .85},
    {'kind': 'bell', 'frequency_hz': 3000, 'gain_db': 1.8, 'q': .9},
    {'kind': 'high_shelf', 'frequency_hz': 6000, 'gain_db': 1., 'slope': 1.},
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rms(signal):
    return float(np.sqrt(np.mean(np.square(signal))))


def db(value):
    return float(20 * np.log10(max(float(value), 1e-12)))


def tone_filter(signal, rate, spec):
    """Causal RBJ EQ applied to the continuous recording before editorial cuts."""
    gain = 10 ** (spec['gain_db'] / 40)
    omega = 2 * np.pi * spec['frequency_hz'] / rate
    cosine = np.cos(omega)
    if spec['kind'] == 'bell':
        alpha = np.sin(omega) / (2 * spec['q'])
        numerator = [1 + alpha * gain, -2 * cosine, 1 - alpha * gain]
        denominator = [1 + alpha / gain, -2 * cosine, 1 - alpha / gain]
    else:
        alpha = np.sin(omega) / 2 * np.sqrt((gain + 1 / gain) * (1 / spec['slope'] - 1) + 2)
        spread = 2 * np.sqrt(gain) * alpha
        numerator = [gain * ((gain + 1) + (gain - 1) * cosine + spread),
                     -2 * gain * ((gain - 1) + (gain + 1) * cosine),
                     gain * ((gain + 1) + (gain - 1) * cosine - spread)]
        denominator = [(gain + 1) - (gain - 1) * cosine + spread,
                       2 * ((gain - 1) - (gain + 1) * cosine),
                       (gain + 1) - (gain - 1) * cosine - spread]
    return lfilter(np.array(numerator) / denominator[0],
                   np.array(denominator) / denominator[0], signal, axis=0)


def main():
    for directory in ('Source', 'Masters', 'Audio'):
        (ROOT / directory).mkdir(exist_ok=True)
    source = ROOT / 'Source' / INPUT.name
    if INPUT.exists():
        source.write_bytes(INPUT.read_bytes())
    if not source.exists():
        raise RuntimeError('The supplied M2011viper.mp3 has not been saved locally.')
    decoded = ROOT / 'Source' / (INPUT.stem + '_decoded_float.wav')
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-v', 'error', '-y', '-i', str(source),
                    '-vn', '-map_metadata', '-1', '-c:a', 'pcm_f32le', str(decoded)], check=True)
    raw, rate = sf.read(decoded, always_2d=True, dtype='float64')
    amplitude = np.max(np.abs(raw), axis=1)
    # Keep a millisecond before the first -50 dBFS sample. This removes encoder
    # pre-roll without cutting into the pressure rise or moving playback clocks.
    active = np.flatnonzero(amplitude > 10 ** (-50 / 20))
    if not len(active):
        raise RuntimeError('No firing transient in the supplied source.')
    first = max(0, int(active[0]) - round(rate * .001))
    tail = np.flatnonzero(amplitude > 10 ** (-65 / 20))
    last = min(len(raw), int(tail[-1]) + 1 + round(rate * .004), first + round(rate * .620))
    # The 45 Hz rolloff removes DC/subsonic content, retaining the measured
    # firearm body. Filter continuously before the cut to preserve its onset.
    filtered = sosfilt(butter(2, 45, 'highpass', fs=rate, output='sos'), raw, axis=0)
    # The new normal shot retains its own timbre with a modest presence lift.
    for spec in TONE_EQ:
        filtered = tone_filter(filtered, rate, spec)
    original = raw[first:last].copy()
    processed = filtered[first:last].copy()
    early = min(len(processed), round(rate * .100))
    fade_in = min(len(processed), max(2, round(rate * .00025)))
    fade_out = min(len(processed) - fade_in, max(2, round(rate * .012)))
    processed[:fade_in] *= np.linspace(0, 1, fade_in)[:, None]
    processed[-fade_out:] *= (np.cos(np.linspace(0, np.pi / 2, fade_out)) ** 2)[:, None]
    # Preserve the initial body/early reflections; progressively end the long
    # source tail so repeated semi-auto shots don't retain a full-second bed.
    seconds = np.arange(len(processed)) / rate
    release = np.clip((seconds - .220) / (.620 - .220), 0, 1)
    processed *= (np.cos(release * np.pi / 2) ** 2)[:, None]
    reference_path = ROOT / 'Inputs/SuppressedLoudnessReference_float.wav'
    reference, reference_rate = sf.read(reference_path, always_2d=True, dtype='float64')
    reference_early = min(len(reference), round(reference_rate * .100))
    energy_gain = rms(reference[:reference_early]) / max(rms(processed[:early]), 1e-12)
    processed *= energy_gain
    # Linked gain preserves the stereo balance and avoids MP3 overshoot becoming
    # integer clipping. No saturation, pitch shift or synthetic sound layers.
    ceiling = 10 ** (-1.3 / 20)
    headroom_gain = min(1., ceiling / max(float(np.max(np.abs(processed))), 1e-12))
    processed *= headroom_gain
    master = ROOT / 'Masters/S_PitViper2011_Fire_float.wav'
    output = ROOT / 'Audio/S_PitViper2011_Fire.wav'
    sf.write(master, processed, rate, subtype='FLOAT')
    sf.write(output, processed, rate, subtype='PCM_16')
    recipe = {
        'revision': 'M2011NormalV3', 'user_feedback': 'Promote BrightV2 to all supported pistol suppressors; use M2011viper for normal Pit Viper firing.',
        'level_reference': str(reference_path.relative_to(ROOT)),
        'input_requested_name': 'M2011viper', 'input_actual_path': str(INPUT),
        'source': str(source.relative_to(ROOT)), 'source_sha256': digest(source),
        'source_kind': 'User-provided local MP3; source rights retained; no publication requested.',
        'decoded': str(decoded.relative_to(ROOT)), 'sample_rate': rate,
        'channels': raw.shape[1], 'source_duration_seconds': len(raw) / rate,
        'source_peak_dbfs': db(np.max(np.abs(raw))),
        'processing': {
            'cut_source_samples': [first, last], 'removed_lead_seconds': first / rate,
            'start_threshold_dbfs': -50, 'lead_preserved_ms': 1,
            'tail_threshold_dbfs': -65, 'tail_margin_ms': 4,
            'highpass_hz': 45, 'filter_order': 2,
            'tone_eq': TONE_EQ,
            'energy_match_window_ms': early / rate * 1000,
            'energy_compensation_gain_db': db(energy_gain),
            'headroom_gain_db': db(headroom_gain), 'peak_ceiling_dbfs': -1.3,
            'fade_in_ms': .25, 'fade_out_ms': 12,
            'tail_release_start_ms': 220, 'tail_release_end_ms': 620,
            'pitch_or_time_shift': False, 'added_sound_layers': False,
            'background_separation': 'No speculative denoising or reconstructed tail.'
        },
        'output': str(output.relative_to(ROOT)), 'output_sha256': digest(output),
        'master': str(master.relative_to(ROOT)), 'master_sha256': digest(master),
        'duration_seconds': len(processed) / rate, 'output_format': 'PCM16 WAV',
        'output_peak_dbfs': db(np.max(np.abs(processed))),
        'early_rms_before_dbfs': db(rms(original[:early])),
        'early_rms_after_dbfs': db(rms(processed[:early])),
        'reference_early_rms_dbfs': db(rms(reference[:reference_early])),
        'early_rms_change_from_bright_v2_db': db(rms(processed[:early]) / rms(reference[:reference_early])),
        'short_clip_measurement': '100 ms RMS for authoring compensation; not LUFS or perceived loudness acceptance.',
        'runtime_asset': TARGET,
        'routing': 'Existing single, dual and staff-offhand PitViper2011 Fire cue.',
        'suppressed_branch': '/Game/Weapons/PistolSharedAudio20261002/S_Pistol_Suppressed; frozen BrightV2 clip.',
        'auditioned': False, 'game_tested': False,
    }
    (ROOT / 'provenance.json').write_text(json.dumps(recipe, ensure_ascii=False, indent=2), encoding='utf8')
    print('PIT_VIPER_FIRE_AUTHORED', json.dumps({
        'duration_ms': round(len(processed) / rate * 1000, 3),
        'lead_removed_ms': round(first / rate * 1000, 3),
        'rate': rate, 'channels': raw.shape[1], 'peak_dbfs': round(recipe['output_peak_dbfs'], 3),
        'revision': recipe['revision'], 'early_rms_change_db': round(recipe['early_rms_change_from_bright_v2_db'], 3)
    }))


if __name__ == '__main__':
    main()
