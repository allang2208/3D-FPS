"""A compressed windup, accelerating rush and a contact-aligned heavy impact."""
from pathlib import Path
import json
import subprocess
import wave
import numpy as np
import imageio_ffmpeg
from scipy.signal import butter, sosfilt

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT / 'SourceAssets/SpiralPillarM14Meshy20261004'
OUT = ROOT / 'ProductionV22'
PLAN = json.loads(Path(__file__).with_name('slam_v22.json').read_text(encoding='utf8'))
SR = 48000
RNG = np.random.default_rng(1422)
PREVIEW = PROJECT / 'SourceAssets/M10ChenXia20261003/AudioScout/Previews'
WET = PREVIEW / '834075_federicoy_wet_slimy_movement_96s_CC0.mp3'

def band(y, low, high):
    return sosfilt(butter(3, [low, high], btype='bandpass', fs=SR, output='sos'), y)

def normalize(y):
    return y / max(1.e-9, float(np.max(np.abs(y))))

def fade(y, attack, release):
    t = np.arange(len(y)) / SR
    return y * np.clip(t / attack, 0., 1.) * np.clip((len(y) / SR - t) / release, 0., 1.)

def place(y, at, gain):
    offset = round(at * SR)
    src, dst = max(0, -offset), max(0, offset)
    count = min(len(y) - src, len(mix) - dst)
    if count > 0:
        mix[dst:dst + count] += y[src:src + count] * gain

def align(y, at, gain):
    place(y, at - np.argmax(np.abs(y)) / SR, gain)

mix = np.zeros(round(PLAN['duration_seconds'] * SR))
wind, contact = PLAN['anticipation_end_seconds'], PLAN['contact_seconds']
# Reuse the established creak/groan sound's front section, compressed into
# the short anticipation. This retains M14's metal-and-flesh identity.
old_wave = ROOT / 'AudioV01/Audio/S_M14_TrunkSlam.wav'
with wave.open(str(old_wave), 'rb') as handle:
    old = np.frombuffer(handle.readframes(handle.getnframes()), dtype='<i2').astype(float) / 32768.
front = old[:round(1.1 * SR)]
short = np.interp(np.linspace(0., len(front) - 1., round((wind - .02) * SR)), np.arange(len(front)), front)
place(normalize(fade(short, .045, .045)), .01, .17)
t = np.arange(round((contact - wind) * SR)) / SR
q = t / (contact - wind)
rush = band(RNG.normal(size=len(t)), 110., 2000.) * q ** 2 * np.clip((1. - q) / .10, 0., 1.)
place(normalize(rush), wind, .22)

# Slice an existing licensed wet-body recording, placing the strongest
# transient on the same 0.55 s frame as the collision and control effects.
raw = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error',
    '-ss', '55', '-t', '3', '-i', str(WET), '-ac', '1', '-ar', str(SR), '-f', 'f32le', 'pipe:1'],
    check=True, capture_output=True).stdout
wet = band(np.frombuffer(raw, dtype='<f4').astype(float), 60., 3000.)
peak = int(np.argmax(np.abs(wet)))
body = wet[max(0, peak - round(.012 * SR)):min(len(wet), peak + round(.42 * SR))]
body = normalize(fade(body, .003, .20))
align(body, contact, .72)
t = np.arange(round(.52 * SR)) / SR
thump = np.sin(2. * np.pi * (75. * t - 30. * t * t)) * np.exp(-t * 13.)
align(normalize(fade(thump, .001, .15)), contact, .55)
clang = sum(gain * np.sin(2. * np.pi * 190. * ratio * t) * np.exp(-t * decay)
            for ratio, gain, decay in ((1., 1., 10.), (1.58, .48, 14.), (2.53, .24, 18.)))
align(normalize(fade(clang, .001, .20)), contact, .20)
t = np.arange(round(.64 * SR)) / SR
rumble = band(RNG.normal(size=len(t)), 35., 160.) * np.exp(-t * 6.)
place(normalize(fade(rumble, .025, .28)), contact + .022, .12)
mix = normalize(fade(mix, .006, .18)) * .90
output = OUT / 'Audio' / (PLAN['sound'] + '.wav')
output.parent.mkdir(parents=True, exist_ok=True)
with wave.open(str(output), 'wb') as handle:
    handle.setnchannels(1)
    handle.setsampwidth(2)
    handle.setframerate(SR)
    handle.writeframes(np.rint(mix * 32767.).astype('<i2').tobytes())
report = dict(revision=PLAN['revision'], wav=str(output), sample_rate=SR, channels=1,
              duration_seconds=PLAN['duration_seconds'], contact_seconds=contact,
              sources=[dict(file=str(old_wave), provenance='AudioV01/Records/audio_source.json; existing authored M14 slam'),
                       dict(file=str(WET), url='https://freesound.org/s/834075/', license='CC0',
                            input_format='existing MP3 preview used by AudioV01')],
              synthetic_layers=['rising rush', 'low body thump', 'bolt clang', 'short rumble'],
              listened=False, runtime_tested=False)
(OUT / 'Records/audio_authoring.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
print('M14_V22_SLAM_AUDIO_AUTHORED ' + str(output))
