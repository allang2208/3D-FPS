"""Cut user-reference reload contacts; local authoring, no playback or testing."""
from pathlib import Path
import hashlib
import json
import subprocess
import tempfile

import imageio_ffmpeg
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'References/PKM_UserReloadReference.mp4'
AUDIO = HERE / 'reference_audio.wav'
RATE = 48000
# Source-video seconds. Event seconds use the actual Reload16 source clock;
# the empty branch removes the old-belt event and advances later contacts .9 s.
CONTACTS = [
    ('CoverOpen', 10.825, 11.340, .65, .72, 'ChargeRelease'),
    ('BeltLift', 11.745, 12.185, 1.65, .74, 'MagOut'),
    ('BoxOut', 12.420, 12.900, 2.60, 1., 'MagOut'),
    ('BoxInsert', 14.245, 14.470, 4.35, 1., 'MagInsert'),
    ('BeltSeat', 15.230, 15.435, 5.10, 1., 'MagSeat'),
    ('CoverClose', 15.865, 16.100, 5.72, 1., 'ChargeRelease'),
    ('ChargePull', 24.710, 24.935, 6.03, 1., 'ChargePull'),
    ('ChargeRelease', 25.010, 25.215, 6.45, 1., 'ChargeRelease'),
]

x, rate = sf.read(AUDIO)
if rate != RATE:
    raise RuntimeError('Reference decode must be 48 kHz')
# Remove DC/low rumble without rebuilding the source's mechanical timbre.
x = sosfiltfilt(butter(2, 80, fs=RATE, btype='highpass', output='sos'), x)
clips = []
with tempfile.TemporaryDirectory(prefix='pkm_reload22_') as temp:
    for name, start, end, contact, tempo, reference in CONTACTS:
        y = x[round(start*RATE):round(end*RATE)].copy()
        if tempo != 1.:
            input_wav, output_wav = Path(temp)/'in.wav', Path(temp)/'out.wav'
            sf.write(input_wav, y, RATE, subtype='FLOAT')
            subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-v', 'error',
                '-i', str(input_wav), '-af', f'atempo={tempo}', '-c:a', 'pcm_f32le',
                str(output_wav)], check=True)
            y, _ = sf.read(output_wav)
        # Preserve attack onset; suppress only cut-boundary clicks and tail cuts.
        attack, release = round(.003*RATE), round(.025*RATE)
        y[:attack] *= np.linspace(0., 1., attack)
        y[-release:] *= np.linspace(1., 0., release)
        clips.append((name, y, start, end, contact, tempo, reference))

# One gain for the set preserves the video's relative impact levels.
gain = 10**(-2./20.) / max(float(np.max(np.abs(c[1]))) for c in clips)
manifest = {
    'source_url': 'https://www.bilibili.com/video/BV1jHeA6sEmj/',
    'source_file': str(SOURCE),
    'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'rights': 'User-selected game-video reference; redistribution rights not established. Keep source and derivatives local.',
    'processing': 'Mono 48 kHz PCM16, 80 Hz highpass, 3 ms attack / 25 ms tail fades; one gain across all cuts, -2 dBFS set peak. Pitch-preserving tempo on cover opening and belt lift only.',
    'common_gain_db': round(float(20*np.log10(gain)), 4),
    'contacts': [],
}
for name, y, start, end, contact, tempo, reference in clips:
    asset = f'S_PKM_{name}'
    wav = HERE / (asset+'.wav')
    sf.write(wav, y*gain, RATE, subtype='PCM_16')
    manifest['contacts'].append({
        'name': name, 'asset_name': asset, 'wav': wav.name,
        'video_start': start, 'video_end': end, 'tempo': tempo,
        'normal_source_time': None if name.startswith('Charge') else contact,
        'empty_source_time': None if name=='BeltLift' else round(contact-(.9 if contact>=2.3 else 0), 3),
        'duration': round(len(y)/RATE, 6),
        'settings_reference': f'/Game/Weapons/AKM/Audio/S_AKM_{reference}',
        'peak_dbfs': round(float(20*np.log10(np.max(np.abs(y*gain)))), 3),
    })
(HERE/'audio_manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps({'clips':len(clips), 'common_gain_db':manifest['common_gain_db'],
    'durations':{c['name']:c['duration'] for c in manifest['contacts']}}))
