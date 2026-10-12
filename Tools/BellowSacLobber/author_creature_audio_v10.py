"""M-09 alert, pressure/spit and death palette. Author only; no playback.

Public Freesound HQ previews are retained honestly as lossy sources. The
downloaded pages retain their CC0 declaration; no login-only master is claimed.
"""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import wave
import requests
import imageio_ffmpeg
import numpy as np
from scipy.signal import butter, sosfilt

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT / 'SourceAssets/BellowSacLobberMeshy20261012/CreatureAudioV10'
SOURCES, OUT = ROOT / 'Sources', ROOT / 'Audio'
SOURCES.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)
SR = 48000
RNG = np.random.default_rng(91012)
remote = {
    'inhale': ('colorsCrimsonTears', 537883, '537/537883_11785387-hq.mp3'),
    'burst': ('JustInvoke', 138477, '138/138477_758593-hq.mp3'),
    'death': ('QuantumFellow', 734841, '734/734841_14713973-hq.mp3'),
}
records, raw = [], {}

def decode(path):
    result = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error',
        '-i', str(path), '-ac', '1', '-ar', str(SR), '-f', 'f32le', 'pipe:1'], check=True, capture_output=True)
    return np.frombuffer(result.stdout, dtype='<f4').astype(np.float64)

for role, (author, sid, preview) in remote.items():
    url = f'https://freesound.org/people/{author}/sounds/{sid}/'
    license_page = SOURCES / f'{sid}_source_page.html'
    if not license_page.exists():
        response = requests.get(url, timeout=45)
        response.raise_for_status()
        if 'creativecommons.org/publicdomain/zero/1.0' not in response.text:
            raise RuntimeError('CC0 declaration missing on source page: ' + url)
        license_page.write_text(response.text, encoding='utf-8')
    path = SOURCES / f'{sid}_{author}_HQ_preview.mp3'
    download = 'https://cdn.freesound.org/previews/' + preview
    if not path.exists():
        response = requests.get(download, timeout=45)
        response.raise_for_status()
        path.write_bytes(response.content)
    raw[role] = decode(path)
    records.append(dict(role=role, author=author, page=url, download=download, license='CC0-1.0',
        file=path.name, original_lossless_master=False, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    print('SOURCE_READY', role, path.name, flush=True)

for role, name, url in [
    ('flesh','635042_sillygrizzlies_blood_gush_squelch_51s_CC0.mp3','https://freesound.org/people/sillygrizzlies/sounds/635042/'),
    ('cavity','695999_samanthacastleberry_stomach_growls_61s_CC0.mp3','https://freesound.org/s/695999/')]:
    source = PROJECT / 'SourceAssets/MantisM27/AudioV1/Sources' / name
    retained = SOURCES / name
    if not retained.exists(): shutil.copy2(source, retained)
    raw[role] = decode(retained)
    records.append(dict(role=role, page=url, license='CC0 per retained M10 AudioScout source record',
        file=name, original_lossless_master=False, sha256=hashlib.sha256(retained.read_bytes()).hexdigest()))

def clock(seconds): return np.arange(round(seconds * SR)) / SR
def blank(seconds): return np.zeros(round(seconds * SR))
def unit(x): return x / max(1.e-9, float(np.max(np.abs(x))))
def band(x, low, high): return sosfilt(butter(3, [low, high], btype='bandpass', fs=SR, output='sos'), x)
def fade(x, attack=.008, release=.06):
    t = np.arange(len(x)) / SR
    return x * np.clip(t / attack, 0., 1.) * np.clip((len(x) / SR - t) / release, 0., 1.)
def tissue(role, start, seconds, low, high, rate=1.):
    positions = (start + clock(seconds) * rate) * SR
    layer = np.interp(positions, np.arange(len(raw[role])), raw[role], left=0., right=0.)
    return unit(fade(band(layer, low, high)))
def air(seconds, low=250., high=5000.):
    return unit(band(RNG.normal(0., 1., len(clock(seconds))), low, high))
def place(mix, layer, at, gain):
    start = round(at * SR)
    count = min(len(layer), len(mix) - start)
    if count > 0: mix[start:start+count] += layer[:count] * gain
def body_thump(seconds, frequency=58.):
    t = clock(seconds)
    return fade((np.sin(2*np.pi*frequency*t) + .27*np.sin(2*np.pi*frequency*1.83*t)) * np.exp(-t*16.), .002, .04)

manifest = dict(revision='CreatureAudioV10', monster='鼓囊 M-09', sample_rate=SR, channels=1,
    sources=records, native_gain=1.35, peak_ceiling_dbfs=-4., listened=False, runtime_tested=False,
    note='48 kHz PCM deliverables derived from CC0 HQ MP3 previews and original synthesized layers; not lossless source masters.', clips={})

def save(role, mix, description):
    # Mild offline saturation adds audible body, with explicit export headroom.
    x = fade(mix - np.mean(mix), .002, .035)
    x = np.tanh(unit(x) * 1.65)
    x = unit(x) * 10**(-4./20.)
    filename = 'S_Bellow_' + role + '.wav'
    with wave.open(str(OUT / filename), 'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR)
        f.writeframes(np.rint(x * 32767.).astype('<i2').tobytes())
    manifest['clips'][role] = dict(file=filename, duration=len(x)/SR, looping=False, description=description)

for role, start, duration in [('AlertA', .12, .84), ('AlertB', .47, .92)]:
    t = clock(duration)
    x = tissue('inhale',start,duration,110.,3700.,.88) * .72
    x += tissue('cavity',9. if role=='AlertA' else 12.,duration,70.,700.) * .16
    x += air(duration,500.,3600.) * np.exp(-t*7.) * .09
    save(role,x,'Short inhaled throat alarm and sac resonance; new confirmed discovery only')

duration=1.2; t=clock(duration); x=blank(duration)
# Pressure builds through density and amplitude, without a cartoon pitch sweep.
x += tissue('cavity',16.,duration,65.,850.) * (.16 + .28*(t/duration)**1.7)
x += air(duration,230.,3400.) * (.05 + .18*(t/duration)**2.1)
for at, length, gain, source_at in [(0.04,.25,.12,20.4),(.42,.31,.19,21.0),(.81,.36,.28,22.0)]:
    place(x,tissue('flesh',source_at,length,130.,2600.),at,gain)
x += .08*np.sin(2*np.pi*76.*t) * np.sin(np.pi*np.clip(t/duration,0,1))**2
save('Charge',fade(x,.09,.045),'Fixed 1.20 s wet pressure build synchronized to nozzle inflation; canceled on interruption')

for role, offset in [('SpitA',20.55),('SpitB',21.3)]:
    duration=.43; t=clock(duration); x=blank(duration)
    place(x,tissue('burst',0.,.20,100.,9500.,.9),0.,.85)
    place(x,body_thump(.30,61. if role=='SpitA' else 66.),0.,.48)
    place(x,tissue('flesh',offset,.28,150.,6000.),.025,.37)
    x += air(duration,480.,6200.)*np.exp(-t*12.)*.16
    save(role,x,'Compact air burst, wet sac separation and weight; only after successful projectile spawn')

for role, start, duration in [('DeathA',.12,2.4),('DeathB',.75,2.65)]:
    t=clock(duration)
    x=tissue('death',start,duration,90.,3300.,.93)*(.58*np.exp(-t*.45))
    x+=air(duration,280.,2600.)*np.exp(-t*1.6)*.13
    x+=tissue('cavity',24. if role=='DeathA' else 28.,duration,70.,700.)*.13*np.exp(-t*.7)
    place(x,tissue('flesh',24.,.5,130.,2300.),.08,.13)
    save(role,fade(x,.025,.5),'Deflating biological death rasp; no baked or timed floor impact')

duration=.55;t=clock(duration);x=blank(duration)
place(x,body_thump(.40,54.),0.,.65)
place(x,tissue('flesh',20.45,.39,90.,4200.),.012,.48)
x+=air(duration,120.,3200.)*np.exp(-t*22.)*.24
save('BodyFall',x,'One wet heavy impact from actual soft-corpse ground contact, speed-scaled')

(ROOT/'audio_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(SOURCES/'README.md').write_text('CC0 source pages and public HQ MP3 previews retained for reconstruction.\n'
    'No original lossless downloads are claimed. Full source URLs, licensing and hashes are in ../audio_manifest.json.\n',encoding='utf-8')
print('BELLOW_CREATURE_AUDIO_V10_AUTHORED',len(manifest['clips']),'PCM waves; no playback.',flush=True)
