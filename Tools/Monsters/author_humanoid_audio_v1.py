"""Shared humanoid-zombie vocal palette (nurse/staff/spitter/fat/mutant3/witch).

Sources are OpenGameArt CC0 packs retained in Sources/ with the license pages.
Lossy/lossless honesty: the starninjas pack ships OGG sources; the Ogrebane
pack ships WAV sources. Deliverables are 48 kHz mono PCM mixes, not masters.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import wave
import imageio_ffmpeg
import numpy as np
from scipy.signal import butter, sosfilt

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT / 'SourceAssets/SharedHumanoidAudio20261016'
SOURCES, OUT = ROOT / 'Sources', ROOT / 'Audio'
OUT.mkdir(parents=True, exist_ok=True)
SR = 48000
RNG = np.random.default_rng(20261016)

PACKS = {
    'starninjas': dict(page='https://opengameart.org/content/16-monster-growls',
        author='StarNinjas', license='CC0-1.0',
        archive='monster_-_starninjas.zip'),
    'ogrebane': dict(page='https://opengameart.org/content/monster-sound-effects-pack',
        author='Ogrebane', license='CC0-1.0',
        archive='monster_sfx_pack.zip'),
}

def decode(path):
    result = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error',
        '-i', str(path), '-ac', '1', '-ar', str(SR), '-f', 'f32le', 'pipe:1'], check=True, capture_output=True)
    return np.frombuffer(result.stdout, dtype='<f4').astype(np.float64)

raw, records = {}, []
def load(role, pack, member):
    path = SOURCES / (member if pack == 'starninjas' else 'monster_sfx_pack/' + member)
    raw[role] = decode(path)
    records.append(dict(role=role, pack=pack, member=member, page=PACKS[pack]['page'],
        author=PACKS[pack]['author'], license=PACKS[pack]['license'], file=str(path.name),
        original_lossless_master=pack != 'starninjas',
        sha256=hashlib.sha256(path.read_bytes()).hexdigest()))

for role, pack, member in [
    ('growl_idle_a', 'starninjas', 'monster.8.ogg'),
    ('growl_idle_b', 'starninjas', 'monster.11.ogg'),
    ('growl_chase', 'starninjas', 'monster.15.ogg'),
    ('grunt_hit_a', 'ogrebane', 'monster-3.wav'),
    ('grunt_hit_b', 'ogrebane', 'monster-7.wav'),
    ('roar_attack', 'ogrebane', 'monster-9.wav'),
    ('roar_death', 'ogrebane', 'monster-6.wav'),
]:
    load(role, pack, member)

def clock(seconds): return np.arange(round(seconds * SR)) / SR
def blank(seconds): return np.zeros(round(seconds * SR))
def unit(x): return x / max(1.e-9, float(np.max(np.abs(x))))
def band(x, low, high): return sosfilt(butter(3, [low, high], btype='bandpass', fs=SR, output='sos'), x)
def fade(x, attack=.008, release=.06):
    t = np.arange(len(x)) / SR
    return x * np.clip(t / attack, 0., 1.) * np.clip((len(x) / SR - t) / release, 0., 1.)
def voice(role, start, seconds, low, high, rate=1.):
    positions = (start + clock(seconds) * rate) * SR
    layer = np.interp(positions, np.arange(len(raw[role])), raw[role], left=0., right=0.)
    return unit(fade(band(layer, low, high)))
def place(mix, layer, at, gain):
    start = round(at * SR)
    count = min(len(layer), len(mix) - start)
    if count > 0: mix[start:start+count] += layer[:count] * gain

manifest = dict(revision='HumanoidAudioV1', scope='M-01 staff + nurse family shared palette',
    sample_rate=SR, channels=1, sources=records, packs=PACKS, listened=False, runtime_tested=False,
    note='48 kHz PCM deliverables derived from OpenGameArt CC0 packs; license pages and hashes retained.', clips={})

def save(role, mix, description, looping=False):
    x = fade(mix - np.mean(mix), .002, .035)
    x = np.tanh(unit(x) * 1.6)
    x = unit(x) * 10**(-4./20.)
    filename = 'S_Humanoid_' + role + '.wav'
    with wave.open(str(OUT / filename), 'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR)
        f.writeframes(np.rint(x * 32767.).astype('<i2').tobytes())
    manifest['clips'][role] = dict(file=filename, duration=round(len(x)/SR, 3), looping=looping, description=description)

# Idle loop: two low-stretched moan phrases separated by a breath gap; the last
# 0.6 s folds back into the head so the seam is a standard crossfade, not a cut.
def moan(role, start, seconds, low, high, rate):
    positions = (start + clock(seconds) * rate) * SR
    layer = np.interp(positions, np.arange(len(raw[role])), raw[role], left=0., right=0.)
    return band(layer, low, high)

dur = 4.4; seam = .6; x = blank(dur)
# Phrase 1: deep dragged growl from the low Ogrebane stock.
place(x, unit(fade(moan('roar_death', .05, 1.9, 70., 900., .62), .18, .45)), .05, .8)
# Phrase 2: softer starninjas growl pitched down into the same register.
place(x, unit(fade(moan('growl_idle_a', .15, 2.0, 70., 1100., .72), .2, .5)), 2.15, .55)
# Continuous quiet breath bed keeps the gap alive without a new tone color.
t = clock(dur)
x += band(RNG.normal(0., 1., len(x)), 120., 700.) * (.05 + .03*np.sin(2*np.pi*t/.9)**2)
x = unit(x) * .82
# Seamless loop: fold the final seam window back onto the head so the breath
# bed and any tail ring continue across the boundary instead of cutting.
x[:round(seam*SR)] += x[-round(seam*SR):]
x = x[:-round(seam*SR)]
x = unit(x) * .8
save('Idle', x, 'Deep two-phrase moan loop with breath bed; quiet spread radius, gated to live states', True)

# Chase bark: sharp attention snarl on the aggro edge.
x = voice('growl_chase', .06, .92, 700., 4600., .94)
x += voice('growl_chase', .30, .92, 180., 900.) * .3
save('Chase', x, 'Sharp nasal discovery bark when Chase starts')

# Attack: deep throat roar for the contact swing.
x = voice('roar_attack', .02, .58, 240., 3000., .9)
x += voice('roar_attack', .12, .58, 900., 5200., 1.06) * .35
save('Attack', x, 'Short hot throat roar at attack contact window')

# Hit grunts: two pain snorts, alternating.
for role, key, start in [('HitA', 'grunt_hit_a', .01), ('HitB', 'grunt_hit_b', .02)]:
    x = voice(key, start, .42 if role == 'HitA' else .46, 300., 3200.)
    x += band(RNG.normal(0., 1., len(x)), 400., 2600.) * np.exp(-clock(len(x)/SR) * 14.) * .12
    save(role, x, 'Short pain grunt on stagger edge')

# Death: extended rasping collapse with wet decay tail.
dur = 1.9; t = clock(dur); x = blank(dur)
place(x, voice('roar_death', .05, 1.2, 160., 2600., .88), 0., 1.)
place(x, voice('roar_death', .55, 1.0, 90., 1400., .72), .55, .5)
x += band(RNG.normal(0., 1., len(x)), 140., 900.) * np.exp(-t * 2.2) * .1
save('Death', fade(x, .015, .55), 'Guttural collapse rasp; loop voice stops at the same edge')

# Footsteps: low shamble thud plus cloth-drag noise; two alternates.
for i, freq in enumerate([52., 58.]):
    dur = .3; t = clock(dur)
    x = (np.sin(2*np.pi*freq*t) + .3*np.sin(2*np.pi*freq*1.9*t)) * np.exp(-t*18.)
    x += band(RNG.normal(0., 1., len(x)), 90., 480.) * np.exp(-t*(14.+i*3.)) * .5
    x += band(RNG.normal(0., 1., len(x)), 1200., 4200.) * np.exp(-t*30.) * .05
    save(f'Step{"AB"[i]}', x, 'Soft bare-foot drag impact, stride-gated by real speed')

(ROOT/'audio_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
(SOURCES/'README.md').write_text('OpenGameArt CC0 packs retained for reconstruction.\n'
    '16 Monster Growls (StarNinjas, CC0): https://opengameart.org/content/16-monster-growls\n'
    'Monster Sound Effects Pack (Ogrebane, CC0): https://opengameart.org/content/monster-sound-effects-pack\n'
    'Hashes per member file are in ../audio_manifest.json.\n', encoding='utf-8')
print('HUMANOID_AUDIO_V1_AUTHORED', len(manifest['clips']), 'PCM waves; no playback.', flush=True)
