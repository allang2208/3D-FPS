"""Mix only M14's revised bite; all timing comes from the animation contract."""
from pathlib import Path
import json
import subprocess
import wave
import numpy as np
import imageio_ffmpeg
from scipy.signal import butter, sosfilt

PROJECT = Path('D:/FPS3D/FPSGAME')
OUT = PROJECT / 'SourceAssets/SpiralPillarM14Meshy20261004/ProductionV21'
SCOUT = PROJECT / 'SourceAssets/M10ChenXia20261003/AudioScout'
PLAN = json.loads(Path(__file__).with_name('bite_v21.json').read_text(encoding='utf8'))
SR = 48000
RNG = np.random.default_rng(1421)
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
SOURCES = {
    'bite': ('467701_lucasduff_monster_bite_2s_CC0.mp3', 'https://freesound.org/s/467701/'),
    'flesh': ('635042_sillygrizzlies_blood_gush_squelch_51s_CC0.mp3', 'https://freesound.org/s/635042/'),
    'breath': ('466830_breviceps_dragon_snarl_roar_attack_3s_CC0.mp3', 'https://freesound.org/s/466830/'),
}

def load(name):
    result = subprocess.run([FFMPEG, '-hide_banner', '-loglevel', 'error', '-i',
        str(SCOUT / 'Previews' / SOURCES[name][0]), '-ac', '1', '-ar', str(SR),
        '-f', 'f32le', 'pipe:1'], check=True, capture_output=True)
    return np.frombuffer(result.stdout, dtype='<f4').astype(np.float64)

def band(signal, low, high):
    return sosfilt(butter(3, [low, high], btype='bandpass', fs=SR, output='sos'), signal)

def normalize(signal):
    return signal / max(1.e-9, float(np.max(np.abs(signal))))

def fade(signal, attack, release):
    t = np.arange(len(signal)) / SR
    return signal * np.clip(t / attack, 0., 1.) * np.clip((len(signal) / SR - t) / release, 0., 1.)

def place(signal, at, gain):
    offset = round(at * SR)
    source_start = max(0, -offset)
    dest_start = max(0, offset)
    count = min(len(signal) - source_start, len(mix) - dest_start)
    if count > 0:
        mix[dest_start:dest_start + count] += signal[source_start:source_start + count] * gain

duration = PLAN['duration_seconds']
anticipate = PLAN['anticipation_end_seconds']
extend = PLAN['maximum_extension_seconds']
contact = PLAN['contact_seconds']
mix = np.zeros(round(duration * SR), dtype=np.float64)
flesh = band(load('flesh'), 140., 2200.)
breath = band(load('breath'), 90., 1500.)
bite = band(load('bite'), 130., 7200.)

# The first half second is soft tissue drawing out, with headroom reserved
# for the bite. Local source slices retain the established organic timbre.
prepare = normalize(fade(flesh[round(20. * SR):round(20.43 * SR)], .16, .10))
place(prepare, .035, .085)
air = normalize(fade(breath[:round(.47 * SR)], .22, .14))
place(air, .055, .065)

# A short rising rush exists only during the 0.25 second extension burst.
t = np.arange(round((extend - anticipate) * SR)) / SR
q = t / (extend - anticipate)
rush = band(RNG.normal(0., 1., len(t)), 180., 2600.)
rush *= q ** 2 * np.clip((1. - q) / .16, 0., 1.)
place(normalize(rush), anticipate, .17)

# Keep only the strongest attack transient, not the source's long wind-up.
# Align its actual sample peak with the jaw's closed/contact frame.
source_peak = int(np.argmax(np.abs(bite)))
start = max(0, source_peak - round(.02 * SR))
snap = fade(bite[start:min(len(bite), source_peak + round(.28 * SR))], .004, .15)
snap_peak = int(np.argmax(np.abs(snap)))
place(normalize(snap), contact - snap_peak / SR, .70)

# A small dry bolt click and a low body thump give the closure weight without
# turning the mouth into a metallic weapon; the wet tail follows afterward.
t = np.arange(round(.22 * SR)) / SR
clang = sum(np.sin(2. * np.pi * 305. * ratio * t) * np.exp(-t * decay) * gain
            for ratio, decay, gain in ((1., 28., 1.), (2.17, 38., .38), (3.71, 48., .22)))
clang += band(RNG.normal(0., 1., len(t)), 2200., 10000.) * np.exp(-t * 270.) * .10
clang = normalize(fade(clang, .001, .08))
place(clang, contact - np.argmax(np.abs(clang)) / SR, .10)
thump = np.sin(2. * np.pi * (100. * t - 110. * t * t)) * np.exp(-t * 32.)
thump = normalize(fade(thump, .001, .10))
place(thump, contact - np.argmax(np.abs(thump)) / SR, .16)
tail = normalize(fade(flesh[round(20.55 * SR):round(21.08 * SR)], .055, .27))
place(tail, contact + .028, .115)

# One state-start SoundWave shares the existing replicated bite clock.
# Short fades remove splice clicks; there is no new Tick, timer or cue delay.
mix = fade(mix, .008, .16)
mix = normalize(mix) * .88
audio = OUT / 'Audio' / (PLAN['sound'] + '.wav')
audio.parent.mkdir(parents=True, exist_ok=True)
with wave.open(str(audio), 'wb') as handle:
    handle.setnchannels(1)
    handle.setsampwidth(2)
    handle.setframerate(SR)
    handle.writeframes(np.rint(mix * 32767.).astype('<i2').tobytes())
report = dict(revision=PLAN['revision'], wav=str(audio), sample_rate=SR, channels=1,
              duration_seconds=duration, contact_seconds=contact,
              anticipation_seconds=anticipate, extension_seconds=extend - anticipate,
              layers=['quiet wet protrusion', 'accelerating air rush', 'aligned bite transient',
                      'small synthetic bolt click and low thump', 'wet withdrawal'],
              sources=[dict(file=str(SCOUT / 'Previews' / file), url=url, license='CC0',
                            input_format='existing MP3 preview, reused from the live AudioV01 production')
                       for file, url in SOURCES.values()],
              provenance=str(SCOUT / 'README.md'), synthetic_layers='locally synthesized numpy noise/partials',
              listened=False, runtime_tested=False)
(OUT / 'Records/audio_authoring.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
print('M14_V21_BITE_AUDIO_AUTHORED ' + str(audio))
