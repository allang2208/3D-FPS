"""Copy the user's active gamedev Super90 sound set; decode only the MP3."""
from pathlib import Path
import hashlib, json, shutil, subprocess, wave
import imageio_ffmpeg
import numpy as np

O = Path(__file__).parent
SOURCE = Path('E:/无尽轮回/长期备份/2026-7-13-1/game-dev')
SOUNDS = SOURCE / 'assets/sounds/weapons'
(O / 'Original').mkdir(exist_ok=True)
(O / 'Wav').mkdir(exist_ok=True)
mapping = {'Fire': 'gunshot_600ms_clean.wav', 'Reload': 'Super90-reload.mp3', 'Bolt': 'bolt_pull_1s_clean.wav'}
recipe = {'source_project': str(SOURCE), 'selection': 'Current SUPER90_ITEM and single-reload finish fallback',
    'source_config': ['src/ui/equip-data-manager.js', 'src/config/gun-ammo.js', 'src/entities/player/subsystems.js'],
    'license_note': 'Existing gamedev assets explicitly selected by the user. Upstream rights are not established by this transfer; the previous Mossberg CC0 provenance does not apply.',
    'audio': {}, 'auditioned': False, 'game_tested': False}
for role, name in mapping.items():
    source = SOUNDS / name
    original = O / 'Original' / name
    shutil.copy2(source, original)
    output = O / 'Wav' / ('S_Super90_' + role + '.wav')
    gain = 1.0
    if source.suffix.lower() == '.wav':
        shutil.copy2(source, output)
        processing = 'Byte-for-byte WAV copy; no filtering, trimming, gain or pitch changes'
    else:
        # Decode as float first to avoid clipping any MP3 reconstruction peaks.
        decoded = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-v', 'error', '-i', str(source),
            '-ar', '44100', '-ac', '2', '-f', 'f32le', 'pipe:1'], check=True, capture_output=True).stdout
        samples = np.frombuffer(decoded, dtype='<f4').reshape(-1, 2)
        peak = float(np.max(np.abs(samples)))
        gain = min(1.0, (32767.0 / 32768.0) / peak) if peak else 1.0
        pcm = np.rint(samples * gain * 32768.0).clip(-32768, 32767).astype('<i2')
        with wave.open(str(output), 'wb') as wav:
            wav.setnchannels(2); wav.setsampwidth(2); wav.setframerate(44100); wav.writeframes(pcm.tobytes())
        processing = 'MP3 decoded to 44.1 kHz stereo PCM16; no filtering, trimming or pitch change; only reconstruction-peak headroom if needed'
    with wave.open(str(output), 'rb') as wav:
        sample_rate, channels, duration = wav.getframerate(), wav.getnchannels(), wav.getnframes() / wav.getframerate()
    recipe['audio'][role] = {'source': str(source), 'original': str(original), 'output': str(output),
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'processing': processing,
        'decode_gain': gain, 'sample_rate': sample_rate, 'channels': channels, 'duration_seconds': duration,
        'asset': '/Game/Weapons/Super90/GameDevAudio20261007/' + output.stem}
(O / 'provenance.json').write_text(json.dumps(recipe, ensure_ascii=False, indent=2), encoding='utf-8')
print('SUPER90_GAMEDEV_AUDIO_PREPARED', ', '.join(recipe['audio']))
