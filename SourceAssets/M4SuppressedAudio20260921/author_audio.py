"""Make full-level M4 suppressor voices from the current M4 fire variants.

Run with the local Python 3.11 environment (NumPy, SciPy and SoundFile).
Level measurements below drive the audio processing; this does not audition or
run gameplay. No pitch/time changes or external sound layers are used.
"""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent
import numpy as np
import soundfile as sf
from scipy.signal import butter, lfilter, sosfilt

for variant in range(1, 5):
    SOURCE = PROJECT / f'SourceAssets/FirearmAudio20260913/M4Punch20260914/S_M4_Original_{variant:02d}.wav'
    x, rate = sf.read(SOURCE, always_2d=True, dtype='float64')
    if rate != 48000:
        raise RuntimeError('This authoring recipe uses the existing 48 kHz M4 source.')
    t = np.arange(len(x)) / rate


    def band(signal, low, high):
        return sosfilt(butter(2, [low, high], btype='bandpass', fs=rate, output='sos'), signal, axis=0)


    def weighted(signal):
        # 48 kHz K-weighting, used over the complete short one-shot, without a
        # 400 ms loudness gate (the source itself is only a short transient).
        shelf = lfilter([1.53512485958697, -2.69169618940638, 1.19839281085285],
                        [1.0, -1.69065929318241, 0.73248077421585], signal, axis=0)
        return lfilter([1.0, -2.0, 1.0],
                       [1.0, -1.99004745483398, 0.99007225036621], shelf, axis=0)


    def rms(signal):
        return float(np.sqrt(np.mean(np.square(signal))))


    source_rms = rms(x)
    source_weighted = rms(weighted(x))


    def master_at_source_level(signal):
        # Stereo-linked saturation keeps headroom while compensating energy removed
        # by timbre filtering. Never reduce either full-shot RMS target below source.
        peak_cap = 0.98

        def driven(gain):
            y = signal * gain
            peak = np.max(np.abs(y), axis=1, keepdims=True)
            limited = peak_cap * np.tanh(peak / peak_cap)
            return y * (limited / np.maximum(peak, 1e-15))

        def ratio(y):
            return min(rms(y) / source_rms, rms(weighted(y)) / source_weighted)

        lo, hi = 0.0, 1.0
        while ratio(driven(hi)) < 1.0001:
            hi *= 2.0
            if hi > 128:
                raise RuntimeError('Cannot reach the requested source level with this recipe.')
        for _ in range(40):
            mid = (lo + hi) * 0.5
            if ratio(driven(mid)) < 1.0001:
                lo = mid
            else:
                hi = mid
        return driven(hi), hi


    recipes = [(2850 + (variant-2)*60, 0.52, 0.0055)]
    body = band(x, 100, 420)
    chamber = band(x, 450, 1800)
    detail = band(x, 1800, 7800)
    outputs = []
    for index, (cutoff, body_gain, delay_seconds) in enumerate(recipes, 1):
        # Round off the sharp blast; retain the original low body and timing.
        core = sosfilt(butter(2, cutoff, btype='lowpass', fs=rate, output='sos'), x, axis=0)
        core *= np.exp(-np.maximum(t - 0.080, 0.0) / 0.150)[:, None]
        y = 0.90 * core + body_gain * body * np.exp(-t / 0.160)[:, None]
        # Very short filtered returns suggest a hollow chamber without a long echo.
        for delay, gain in [(delay_seconds, 0.14), (delay_seconds * 1.9, 0.065)]:
            frames = round(delay * rate)
            tap = np.zeros_like(x)
            tap[frames:] = chamber[:-frames]
            y += gain * tap * np.exp(-t / 0.075)[:, None]
        # Keep some original mechanical texture, especially after the initial blast.
        detail_envelope = 0.08 + 0.14 * np.clip((t - 0.018) / 0.024, 0.0, 1.0)
        y += detail * (detail_envelope * np.exp(-t / 0.130))[:, None]
        fade = round(0.002 * rate)
        y[-fade:] *= np.linspace(1.0, 0.0, fade)[:, None]
        y, drive = master_at_source_level(y)
        name = f'S_M4_Suppressed_{variant:02d}'
        destination = HERE / (name + '.wav')
        sf.write(destination, y, rate, subtype='PCM_24')
        outputs.append({
            'asset': name, 'wav': str(destination),
            'lowpass_hz': cutoff, 'body_gain': body_gain,
            'chamber_delay_seconds': delay_seconds, 'master_drive': drive,
            'rms_db_relative_to_source': 20 * np.log10(rms(y) / source_rms),
            'weighted_energy_db_relative_to_source': 20 * np.log10(rms(weighted(y)) / source_weighted),
            'sample_peak': float(np.max(np.abs(y))),
        })

    manifest = {
        'source': str(SOURCE),
        'original_source': 'SourceAssets/FirearmAudio20260913/M4Punch20260914; original M4HK416AudioEmpty20260909/Audio/fire.wav',
        'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'rights': 'Existing M4 source rights retained; not a new CC0 asset.',
        'recipe': 'Current M4 source only; filtered blast, retained low body/mechanics, short chamber returns; compensated source level.',
        'sample_rate': rate, 'channels': x.shape[1], 'duration_seconds': len(x) / rate,
        'pitch_multiplier': 1.0, 'runtime_volume_multiplier': 'Same as normal M4 fire.',
        'source_rms': source_rms, 'source_weighted_rms': source_weighted,
        'outputs': outputs,
        'listening_or_gameplay_tested': False,
    }
    (HERE / f'provenance-{variant:02d}.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'authored': len(outputs), 'seconds': len(x) / rate,
                      'level_compensation': [{k: v for k, v in item.items() if k in
                        ('asset', 'rms_db_relative_to_source', 'weighted_energy_db_relative_to_source', 'sample_peak')}
                        for item in outputs]}, indent=2))
