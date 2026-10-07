"""Mantis M27: wet membrane, scythe edge and restraint-chain sound palette.

48 kHz mono PCM; offline layered authoring, no listening or gameplay tests.
Organic layers reuse the project's documented CC0 preview recordings. Air,
chain, membrane resonance and low impacts are newly synthesized here.
"""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import wave
import imageio_ffmpeg
import numpy as np
from scipy.signal import butter, sosfilt

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT / 'SourceAssets/MantisM27/AudioV1'
OUT = ROOT / 'Audio'
SOURCES = ROOT / 'Sources'
for directory in [OUT, SOURCES]: directory.mkdir(parents=True, exist_ok=True)
SCOUT = PROJECT / 'SourceAssets/M10ChenXia20261003/AudioScout'
SR = 48000
RNG = np.random.default_rng(27017)
source_specs = {
    'flesh': ('635042_sillygrizzlies_blood_gush_squelch_51s_CC0.mp3', 'https://freesound.org/s/635042/'),
    'slime': ('834075_federicoy_wet_slimy_movement_96s_CC0.mp3', 'https://freesound.org/s/834075/'),
    'cavity': ('695999_samanthacastleberry_stomach_growls_61s_CC0.mp3', 'https://freesound.org/s/695999/'),
}
records = []
raw = {}
for role, (filename, url) in source_specs.items():
    source = SCOUT / 'Previews' / filename
    retained = SOURCES / filename
    if not retained.exists(): shutil.copy2(source, retained)
    data = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error',
        '-i', str(retained), '-ac', '1', '-ar', str(SR), '-f', 'f32le', 'pipe:1'],
        check=True, capture_output=True).stdout
    raw[role] = np.frombuffer(data, dtype='<f4').astype(np.float64)
    records.append(dict(role=role, file=str(retained), url=url, license='CC0 per existing AudioScout source record',
        input_format='existing MP3 preview recording, not an original lossless master',
        sha256=hashlib.sha256(retained.read_bytes()).hexdigest()))

def clock(duration): return np.arange(round(duration * SR)) / SR
def blank(duration): return np.zeros(round(duration * SR))
def noise(duration): return RNG.normal(0., 1., round(duration * SR))
def band(y, lo, hi): return sosfilt(butter(3, [lo, hi], btype='bandpass', fs=SR, output='sos'), y)
def unit(y): return y / max(1.e-9, float(np.max(np.abs(y))))
def fade(y, attack=.004, release=.05):
    t = np.arange(len(y)) / SR
    return y * np.clip(t / attack, 0., 1.) * np.clip((len(y) / SR - t) / release, 0., 1.)
def tissue(role, start, duration, lo=100., hi=2800., reverse=False):
    y = raw[role][round(start * SR):round((start + duration) * SR)].copy()
    if reverse: y = y[::-1]
    return unit(fade(band(y, lo, hi), .012, min(.09, duration * .25)))
def place(mix, layer, at, gain=1.):
    first = round(at * SR); length = min(len(layer), len(mix)-first)
    if first >= 0 and length > 0: mix[first:first+length] += layer[:length] * gain
def chain(duration=.13, base=910.):
    t = clock(duration)
    y = sum(g * np.sin(2*np.pi*base*r*t) * np.exp(-d*t)
            for r,g,d in [(1.,.5,38.),(1.63,.3,51.),(2.79,.17,74.),(4.11,.07,100.)])
    y += band(noise(duration), 2600., 10000.) * np.exp(-t*170.) * .13
    return unit(fade(y, .001, .025))
def membrane(duration, f0=130., f1=65.):
    t = clock(duration)
    phase = 2*np.pi*(f0*t+(f1-f0)*t*t/(2*duration))
    return fade((np.sin(phase)+.3*np.sin(phase*1.47))*np.exp(-t*5.),.005,.06)
def seam_loop(y, seconds, overlap=.35):
    n = round(seconds*SR); cross = round(overlap*SR)
    result = y[cross:cross+n].copy()
    a = np.linspace(0.,1.,cross)
    result[-cross:] = y[n:n+cross]*(1.-a) + y[:cross]*a
    return result

manifest = dict(revision='AudioV1', display_name='螳螂 M27', sample_rate=SR, channels=1,
    format='16-bit PCM WAV', sources=records,
    original_layers='deterministic filtered noise, membrane resonances, inharmonic chain partials, short low thumps',
    listened=False, runtime_tested=False, clips={})
def save(role, mix, description, looping=False, landmarks=None):
    y = mix-np.mean(mix)
    # Preserve authored level relationships; only attenuate if headroom needs it.
    y *= min(1., .84/max(1.e-9,float(np.max(np.abs(y)))))
    if not looping: y=fade(y,.001,.018)
    filename = 'S_M27_'+role+'.wav'
    with wave.open(str(OUT/filename),'wb') as handle:
        handle.setnchannels(1); handle.setsampwidth(2); handle.setframerate(SR)
        handle.writeframes(np.rint(y*32767.).astype('<i2').tobytes())
    manifest['clips'][role]=dict(file=filename, seconds=len(y)/SR, looping=looping,
        description=description, landmarks_seconds=landmarks or {})

# Transformation: pressure folds inward, leaving a trembling wet film.
t=clock(.65); y=blank(.65)
air=unit(band(noise(.65),180.,7200.))
y += air*np.exp(-((t-.27)/.115)**2)*.53
place(y,tissue('slime',12.,.42,190.,3800.,True),.02,.27)
place(y,membrane(.35,180.,45.),.27,.20)
place(y,chain(.12,1250.),.11,.075)
save('CloakEnter',y,'Inward membrane suction, a small chain pull, then pressure collapse',landmarks={'collapse':.30})

duration=3.; overlap=.35; t=clock(duration+overlap)
y=band(noise(duration+overlap),380.,1900.)*(.085+.035*np.sin(2*np.pi*1.7*t))
y += .018*np.sin(2*np.pi*83*t+.8*np.sin(2*np.pi*.66*t))
y += .012*np.sin(2*np.pi*121*t)*(1.+.4*np.sin(2*np.pi*3.2*t))
y += np.resize(tissue('slime',31.,duration+overlap,180.,1300.),len(t))*.07
save('CloakLoop',seam_loop(y,duration,overlap),'Quiet gelatin shimmer; short-range positioning detail',True)

for role, force in [('CloakExit',.64),('ShadowBreak',1.)]:
    t=clock(.38); y=unit(band(noise(.38),700.,7400.))*np.exp(-t*25.)*.42*force
    place(y,membrane(.29,210.,72.),0.,.30*force)
    place(y,tissue('flesh',20.55,.24,220.,5500.),.007,.24*force)
    place(y,chain(.16,1040.),.026,.19*force)
    save(role,y,'Membrane snap into visibility'+('; accented ambush rupture' if role=='ShadowBreak' else ''))

# Full 0.65 s melee cue starts with the existing replicated attack clock.
# No flesh impact in these files: a hit is a separate confirmed-damage event.
for role, shift in [('SlashLeft',0.),('SlashRight',170.)]:
    t=clock(.65); y=blank(.65)
    place(y,chain(.115,840.+shift),.042,.105)
    place(y,tissue('slime',22.+shift/170.,.14,150.,1900.),.027,.065)
    rush=unit(band(noise(.65),480.+shift,8200.))
    whoosh=np.exp(-((t-.258)/.034)**2)*np.clip((t-.175)/.08,0.,1.)
    y += rush*whoosh*.72
    y += unit(band(noise(.65),95.,780.))*np.exp(-((t-.255)/.055)**2)*.29
    # Dry ringing and a rapidly falling wake mark braking, not another hit.
    place(y,chain(.16,1410.+shift),.281,.16)
    place(y,membrane(.19,115.,52.),.287,.085)
    save(role,y,'Side-loaded chain tension, accelerated horizontal blade air cut, dry brake and short wake',
         landmarks={'cut_start':.195,'air_cut_peak':.258,'braking':.275})

for role, source_at in [('ScytheHitA',20.45),('ScytheHitB',21.2)]:
    t=clock(.26); y=blank(.26)
    impact=tissue('flesh',source_at,.22,110.,6500.)
    # Compact the wet attack under a purpose-built crisp leading transient.
    place(y,impact,0.,.38)
    y += unit(band(noise(.26),1300.,10500.))*np.exp(-t*110.)*.40
    place(y,membrane(.22,155.,58.),0.,.42)
    place(y,chain(.10,680.),.003,.075)
    save(role,y,'Short wet cut and bone crack; accepted damage only')

t=clock(.60); y=blank(.60)
place(y,tissue('cavity',9.,.52,90.,850.),.015,.16)
place(y,tissue('slime',15.,.30,180.,2100.),.12,.11)
for at,gain,freq in [(.10,.13,740.),(.27,.17,880.),(.46,.24,1020.)]: place(y,chain(.11,freq),at,gain)
y += unit(band(noise(.60),160.,2200.))*np.clip(t/.58,0.,1.)**3*.23
save('PounceWindup',y,'Compressed chest breath and tightening shackles; clear pre-launch warning',landmarks={'launch_boundary':.60})

t=clock(.90); y=blank(.90)
y += unit(band(noise(.90),120.,1200.))*np.exp(-((t-.032)/.038)**2)*.54
y += unit(band(noise(.90),750.,7000.))*(np.exp(-t*4.)*.20+np.exp(-((t-.54)/.095)**2)*.44)
place(y,chain(.16,760.),0.,.14)
place(y,membrane(.24,130.,48.),0.,.28)
save('PounceFlight',y,'Takeoff burst and overhead scythes accelerating down through air; no baked landing',
     landmarks={'takeoff':0.,'downstroke':.34,'blade_rush_peak':.54})

t=clock(.80); y=blank(.80)
place(y,membrane(.31,115.,38.),0.,.63)
y += unit(band(noise(.80),180.,4600.))*np.exp(-t*21.)*.38
place(y,chain(.25,580.),.008,.26)
place(y,chain(.18,970.),.05,.13)
place(y,tissue('slime',17.,.35,130.,2600.),.035,.19)
save('PounceLand',y,'Real ground contact: body thump, paired scythe clack, short wet settle',landmarks={'ground_contact':0.})

t=clock(.36); y=tissue('cavity',12.,.36,140.,1750.)*.19
y += unit(band(noise(.36),700.,3300.))*np.exp(-t*18.)*.19
place(y,membrane(.23,240.,105.),.005,.15)
save('Hurt',y,'Short constricted membrane rasp; rate limited under automatic fire')

t=clock(1.35); y=tissue('cavity',16.,1.35,80.,1450.)*.27
y += unit(band(noise(1.35),280.,2400.))*np.exp(-t*2.8)*.12
place(y,membrane(.70,110.,32.),.08,.20)
place(y,tissue('slime',28.,.64,110.,2200.),.28,.15)
place(y,chain(.20,690.),.23,.11); place(y,chain(.22,540.),.76,.08)
save('Death',y,'Air escaping the torso mouth and slack restraints; no assumed corpse impact time')

for role,duration,at,gain in [('Idle',3.2,24.,.12),('Move',2.,26.,.18)]:
    overlap=.35; t=clock(duration+overlap)
    layer=tissue('slime' if role=='Move' else 'cavity',at,duration+overlap,100.,1600.)
    y=layer*gain+band(noise(duration+overlap),210.,950.)*.022
    if role=='Move':
        for offset in [.15,.56,1.04,1.57]: place(y,chain(.14,780.+offset*70),offset,.055)
    save(role,seam_loop(y,duration,overlap),
         'Subtle motion-gated wet restraint rustle, not fabricated foot contacts' if role=='Move' else 'Low torso-mouth membrane breathing',True)

(ROOT/'audio_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(SOURCES/'README.md').write_text('Source recordings retained from the local M10 AudioScout CC0 collection.\n'
    'These are MP3 previews, not lossless source masters. See ../audio_manifest.json for URLs and hashes.\n',encoding='utf-8')
print(f'M27_AUDIO_V1_AUTHORED {len(manifest["clips"])} waves; no listening or gameplay test performed.')
