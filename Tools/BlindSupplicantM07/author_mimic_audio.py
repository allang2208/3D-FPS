"""Author M07 wall speech from an installed offline SAPI voice; never play it.

Run author_mimic_audio.ps1 first. This module only performs production conversion
and writes audio and a receipt. It does not run audio, runtime, or engine tests.
"""

from __future__ import annotations

import argparse
import json
import wave
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import uniform_filter1d
from scipy.signal import butter, resample_poly, sosfilt


SAMPLE_RATE = 44100
FINAL_SECONDS = 8.0


def read_pcm16_for_conversion(path: Path) -> tuple[np.ndarray, int, dict]:
    with wave.open(str(path), 'rb') as stream:
        rate = stream.getframerate()
        channels = stream.getnchannels()
        width = stream.getsampwidth()
        frames = stream.getnframes()
        if width != 2 or stream.getcomptype() != 'NONE':
            raise ValueError('SAPI production source must use uncompressed 16-bit PCM.')
        samples = np.frombuffer(stream.readframes(frames), dtype='<i2').astype(np.float64) / 32768.0
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    return samples, rate, {
        'sample_rate_hz': rate,
        'channels': channels,
        'pcm_bits': width * 8,
        'frames': frames,
        'duration_seconds': frames / rate,
    }


def filtered(samples: np.ndarray, cutoffs, kind: str, order: int = 3) -> np.ndarray:
    return sosfilt(butter(order, cutoffs, btype=kind, fs=SAMPLE_RATE, output='sos'), samples)


def add_delayed(target: np.ndarray, source: np.ndarray, seconds: float, gain: float) -> None:
    delay = round(seconds * SAMPLE_RATE)
    available = min(len(source), len(target) - delay)
    if available > 0:
        target[delay:delay + available] += source[:available] * gain


def author(audio_dir: Path) -> dict:
    raw_path = audio_dir / 'M07_WallMimic_RawHuihui.wav'
    final_path = audio_dir / 'SC_M07_WallMimic.wav'
    source_meta_path = audio_dir / 'tts_source.json'
    source_meta = json.loads(source_meta_path.read_text(encoding='utf-8-sig'))
    samples, source_rate, raw_format = read_pcm16_for_conversion(raw_path)
    if source_rate != SAMPLE_RATE:
        samples = resample_poly(samples, SAMPLE_RATE, source_rate)

    # Slightly lengthen/lower the installed synthetic voice. Preserve syllables.
    samples = resample_poly(samples, 102, 100)
    maximum_source_samples = round(6.75 * SAMPLE_RATE)
    timing_compressed = len(samples) > maximum_source_samples
    if timing_compressed:
        old_positions = np.arange(len(samples), dtype=np.float64)
        new_positions = np.linspace(0.0, len(samples) - 1, maximum_source_samples)
        samples = np.interp(new_positions, old_positions, samples)

    speech = filtered(samples, [105.0, 2900.0], 'bandpass')
    envelope = np.sqrt(np.maximum(uniform_filter1d(speech * speech, size=441), 0.0))
    rng = np.random.default_rng(700103)
    breath = filtered(rng.standard_normal(len(speech)), [650.0, 4200.0], 'bandpass')
    breath_rms = max(float(np.sqrt(np.mean(breath * breath))), 1.0e-12)
    breath /= breath_rms
    direct = 0.88 * speech + 0.10 * breath * envelope

    final_frames = round(FINAL_SECONDS * SAMPLE_RATE)
    output = np.zeros(final_frames, dtype=np.float64)
    leading_silence_seconds = 0.42
    add_delayed(output, direct, leading_silence_seconds, 1.0)
    wall_reflection = filtered(direct, 1750.0, 'lowpass')
    reflections = [(0.083, 0.22), (0.19, 0.12), (0.37, 0.07), (0.59, 0.04)]
    for delay, gain in reflections:
        add_delayed(output, wall_reflection, leading_silence_seconds + delay, gain)
    lower_reflection = filtered(direct, [150.0, 800.0], 'bandpass')
    add_delayed(output, lower_reflection, leading_silence_seconds + 0.041, 0.10)

    fade_frames = round(0.30 * SAMPLE_RATE)
    output[:fade_frames] *= np.linspace(0.0, 1.0, fade_frames)
    output[-fade_frames:] *= np.linspace(1.0, 0.0, fade_frames)
    # Quiet cue production target. Runtime volume/attenuation belongs to actor authoring.
    peak_target = 0.23
    peak = max(float(np.max(np.abs(output))), 1.0e-12)
    output *= peak_target / peak
    pcm = np.rint(np.clip(output, -1.0, 1.0) * 32767.0).astype('<i2')
    with wave.open(str(final_path), 'wb') as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(SAMPLE_RATE)
        stream.writeframes(pcm.tobytes())

    receipt = {
        'stage': 'local_temporary_wall_mimic_audio_authored',
        'source_text': source_meta['source_text'],
        'raw_file': str(raw_path),
        'final_file': str(final_path),
        'source_metadata_file': str(source_meta_path),
        'raw_format': raw_format,
        'final_format': {
            'sample_rate_hz': SAMPLE_RATE,
            'channels': 1,
            'pcm_bits': 16,
            'frames': final_frames,
            'duration_seconds': FINAL_SECONDS,
            'encoding': 'RIFF WAVE uncompressed little endian PCM',
        },
        'production_recipe': {
            'sapi_voice_rate': source_meta['sapi_voice_rate'],
            'voice_duration_ratio': 1.02,
            'source_timing_compressed_to_fit': timing_compressed,
            'direct_bandpass_hz': [105.0, 2900.0],
            'breath_bandpass_hz': [650.0, 4200.0],
            'breath_envelope_window_seconds': 0.01,
            'direct_gain': 0.88,
            'breath_gain': 0.10,
            'reflection_lowpass_hz': 1750.0,
            'reflection_delay_seconds_and_gain': reflections,
            'leading_silence_seconds': leading_silence_seconds,
            'fade_seconds': 0.30,
            'peak_production_target_dbfs': float(20.0 * np.log10(peak_target)),
            'deterministic_noise_seed': 700103,
        },
        'provenance': {
            'voice_name': source_meta['voice_name'],
            'voice_vendor': source_meta['voice_vendor'],
            'voice_token_id': source_meta['voice_token_id'],
            'generation': 'Installed Windows SAPI desktop voice, offline file output.',
            'use_scope': source_meta['use_scope'],
            'redistribution_license_reviewed': False,
            'real_person_voice_cloned': False,
            'network_used': False,
            'final_actor_performance': False,
        },
        'audio_played': False,
        'runtime_tested': False,
        'engine_imported': False,
        'created_utc': datetime.now(timezone.utc).isoformat(),
    }
    (audio_dir / 'audio_production.json').write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    print(json.dumps({
        'stage': receipt['stage'],
        'final_file': str(final_path),
        'duration_seconds': FINAL_SECONDS,
        'raw_duration_seconds': raw_format['duration_seconds'],
        'runtime_tested': False,
        'audio_played': False,
    }, ensure_ascii=False))
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audio-dir', type=Path, required=True)
    options = parser.parse_args()
    author(options.audio_dir.resolve())
