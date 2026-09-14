"""Author cleaned, contact-aligned 715 audio from the user's local recordings.

Phase identities are editorial inferences from transient groups and action order;
there is no synchronized source video. This script is production, not a PIE test.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import ndimage, signal
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
ASSET_ROOT = '/Game/Weapons/DanWesson715/RecordedAudio20260914'
for directory in ('Cleaned', 'Waves', 'Preview', 'Analysis'):
    (ROOT / directory).mkdir(exist_ok=True)

# start, end, contact transient in the recording; animation contact is in the
# canonical 3.6-second speedloader action. Preserve preceding clacks as pre-roll.
STAGES = [
    dict(name='Open', label='Open cylinder', start=.305, end=.555, anchor=.4125, contact=.48, peak=.52),
    dict(name='Eject', label='Empty-only eject', start=1.800, end=2.230, anchor=2.0575, contact=1.03, peak=.46, empty_only=True),
    dict(name='Retrieve', label='Retrieve loader', start=2.780, end=3.030, anchor=2.8475, contact=1.44, peak=.20),
    dict(name='Insert', label='Insert cartridges', start=3.190, end=3.760, anchor=3.6125, contact=2.20, peak=.42),
    dict(name='Release', label='Release cartridges', start=3.895, end=4.040, anchor=3.9375, contact=2.42, peak=.33),
    dict(name='Withdraw', label='Withdraw loader', start=4.080, end=4.385, anchor=4.2825, contact=2.68, peak=.18),
    dict(name='Close', label='Close cylinder', start=4.940, end=5.420, anchor=5.0075, contact=3.05, peak=.58),
]


def clean(x, sr, highpass, quiet, strength, floor):
    """Zero-phase wind roll-off plus a shared stereo soft spectral mask."""
    filtered = signal.sosfiltfilt(signal.butter(3, highpass, fs=sr, btype='highpass', output='sos'), x, axis=0)
    f, t, z = signal.stft(filtered.T, fs=sr, nperseg=2048, noverlap=1792, boundary='zeros')
    power = np.mean(abs(z)**2, axis=0)
    noise_frames = np.zeros(len(t), dtype=bool)
    for a, b in quiet:
        noise_frames |= (t >= a) & (t <= b)
    noise = np.quantile(power[:, noise_frames], .65, axis=1)
    gain = np.sqrt(np.clip(1 - strength * noise[:, None] / (power + 1e-16), floor**2, 1))
    gain = ndimage.gaussian_filter(gain, sigma=(.8, .65))
    # Preserve strong mechanical transients instead of smearing their attack.
    gain = np.maximum(gain, np.where(power > 18 * noise[:, None], .94, floor))
    _, y = signal.istft(z * gain[None, :, :], fs=sr, nperseg=2048, noverlap=1792, boundary=True)
    return y.T[:len(x)]


def fade(x, sr, attack=.002, release=.018):
    y = x.copy()
    n = min(round(sr * attack), len(y) // 2)
    m = min(round(sr * release), len(y) // 2)
    y[:n] *= np.sin(np.linspace(0, np.pi / 2, n))[:, None]**2
    y[-m:] *= np.cos(np.linspace(0, np.pi / 2, m))[:, None]**2
    return y


def level(x, target, max_gain=4.):
    gain = min(max_gain, target / max(float(np.max(abs(x))), 1e-12))
    return x * gain, gain


def write(path, x, sr):
    sf.write(ROOT / path, x, sr, subtype='PCM_16')


def quiet_band_rms(x, sr, spans, low, high):
    y = signal.sosfiltfilt(signal.butter(3, [low, high], fs=sr, btype='bandpass', output='sos'), x, axis=0)
    samples = np.concatenate([y[round(a * sr):round(b * sr)] for a, b in spans])
    return float(np.sqrt(np.mean(samples**2)))


reload_raw, sr = sf.read(ROOT / 'Original/715-reloading.mp3', always_2d=True)
quiet_spans = [(.65, 1.65), (2.28, 2.65), (4.47, 4.82), (5.60, 6.35)]
reload_clean = clean(reload_raw, sr, 200, quiet_spans, 1.35, .075)
fire_raw, fire_sr = sf.read(ROOT / 'Original/715-fire.mp3', always_2d=True)
# Only the pre-shot lead is used as the noise profile; the decay is not noise.
fire_clean = clean(fire_raw, fire_sr, 85, [(0., .016)], .75, .45)
write('Cleaned/715-reloading-wind-reduced.wav', fade(level(reload_clean, .65)[0], sr), sr)
write('Cleaned/715-fire-wind-reduced.wav', fade(level(fire_clean, .50)[0], fire_sr, .001, .025), fire_sr)
# Float references preserve decoded MP3 peaks above 0 dBFS without clipping.
sf.write(ROOT / 'Analysis/715-fire-decoded.wav', fire_raw, fire_sr, subtype='FLOAT')
sf.write(ROOT / 'Analysis/715-reloading-decoded.wav', reload_raw, sr, subtype='FLOAT')

manifest = {
    'source': 'User supplied D:/FPS3D/资产/715; no synchronized source video',
    'rights': 'User-authorized local game integration; redistribution rights unspecified; do not publish source or derived audio',
    'phase_classification': 'inferred from transient chronology; not confirmed by listening or source video',
    'sample_rate': sr, 'channels': reload_raw.shape[1], 'format': 'PCM16 WAV',
    'asset_root': ASSET_ROOT,
    'processing': {'reload_highpass_hz': 200, 'fire_highpass_hz': 85, 'stft_size': 2048, 'hop': 256,
                   'reload_noise_spans': quiet_spans, 'reload_soft_mask_floor': .075,
                   'fire_soft_mask_floor': .45, 'shared_stereo_mask': True, 'time_stretch': False},
    'originals': {}, 'quiet_band_reduction_db_before_normalization': {}, 'clips': [],
}
for name in ('715-fire.mp3', '715-reloading.mp3'):
    p = ROOT / 'Original' / name
    manifest['originals'][name] = {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size}
for low, high in ((20, 200), (200, 1000), (1000, 12000)):
    before = quiet_band_rms(reload_raw, sr, quiet_spans, low, high)
    after = quiet_band_rms(reload_clean, sr, quiet_spans, low, high)
    manifest['quiet_band_reduction_db_before_normalization'][f'{low}-{high}Hz'] = float(20 * np.log10(before / max(after, 1e-12)))

fire = fade(fire_clean[round(.040 * fire_sr):], fire_sr, .001, .030)
fire, gain = level(fire, .50)
fire_name = 'S_DW715_Fire_Recorded'
write(f'Waves/{fire_name}.wav', fire, fire_sr)
manifest['fire'] = {'asset': fire_name, 'source_start': .040, 'source_end': len(fire_raw)/fire_sr,
                    'gain_db': float(20*np.log10(gain)), 'peak': float(np.max(abs(fire))),
                    'runtime_gain': .562341 * 1.5 * 2, 'timing': 'played on actual shot; 40 ms source lead removed'}

clips = []
for stage in STAGES:
    clip = fade(reload_clean[round(stage['start'] * sr):round(stage['end'] * sr)], sr)
    clip, gain = level(clip, stage['peak'])
    name = 'S_DW715_Loader_' + stage['name']
    write(f'Waves/{name}.wav', clip, sr)
    clips.append(clip)
    manifest['clips'].append({**stage, 'asset': name, 'lead_seconds': round(stage['anchor'] - stage['start'], 6),
                             'gain_db': float(20*np.log10(gain)), 'output_peak': float(np.max(abs(clip))),
                             'duration': len(clip)/sr, 'empty_only': stage.get('empty_only', False)})

# Offline editorial references, mixed at the same per-cue gain as the 715 voice.
# These are not captured gameplay and do not include the game's master mixer.
for empty, duration in ((False, 3.6), (True, 3.85)):
    output = np.zeros((round((duration+.20)*sr), reload_raw.shape[1]))
    for stage, clip in zip(manifest['clips'], clips):
        if stage['empty_only'] and not empty:
            continue
        start = max(0, round((stage['contact'] * duration / 3.6 - stage['lead_seconds']) * sr))
        output[start:start+len(clip)] += clip * (.630957 * 2)
    write(f'Preview/715-speedloader-{"empty" if empty else "tactical"}-editorial.wav', output, sr)
    manifest.setdefault('preview', {})['empty' if empty else 'tactical'] = {
        'duration': duration, 'peak': float(np.max(abs(output))), 'kind': 'offline editorial reference, not gameplay'}

(ROOT/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

fig, axes = plt.subplots(3, 1, figsize=(15, 9), layout='constrained')
step = 96; times = np.arange(0, len(reload_raw), step)/sr
for ax, x, title in zip(axes[:2], (reload_raw, reload_clean), ('Original reload (same gain)', 'Wind reduced (same gain; before clip leveling)')):
    ax.plot(times, x[::step].mean(axis=1), lw=.6, color='#365879')
    ax.set(title=title, xlim=(0, len(x)/sr), ylim=(-1, 1), ylabel='Amplitude'); ax.grid(alpha=.18)
    for i, stage in enumerate(STAGES):
        ax.axvspan(stage['start'], stage['end'], alpha=.10, color=f'C{i}')
        ax.axvline(stage['anchor'], lw=.75, alpha=.65, color=f'C{i}')
        if ax == axes[1]:
            ax.text(stage['anchor'], .65 if i%2==0 else -.82, stage['name'], fontsize=9, ha='center')
ax = axes[2]
for i, stage in enumerate(manifest['clips']):
    start = stage['contact'] - stage['lead_seconds']
    ax.barh(i, stage['duration'], left=start, color=f'C{i}', alpha=.65)
    ax.plot(stage['contact'], i, 'k|', markersize=18)
ax.set(yticks=range(7), yticklabels=[s['label'] for s in STAGES], xlim=(0, 3.6),
       title='3.6s animation contact mapping (inferred identities; eject omitted for tactical reload)', xlabel='Seconds')
ax.invert_yaxis(); ax.grid(axis='x', alpha=.2)
fig.savefig(ROOT/'Analysis/715-cleanup-and-phase-map.png', dpi=140)
print(json.dumps({'authored_assets': 8, 'quiet_band_reduction_db': manifest['quiet_band_reduction_db_before_normalization'],
                  'preview': manifest['preview']}, indent=2))
