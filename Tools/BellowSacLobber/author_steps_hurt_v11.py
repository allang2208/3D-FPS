"""Author M-09 wet padded feet and short hit rasps from retained CC0 sources.

No source downloads, playback, gameplay or analysis tests. Keep V10 untouched.
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

PROJECT=Path('D:/FPS3D/FPSGAME')
PREVIOUS=PROJECT/'SourceAssets/BellowSacLobberMeshy20261012/CreatureAudioV10'
ROOT=PROJECT/'SourceAssets/BellowSacLobberMeshy20261012/StepsHurtV11'
OUT=ROOT/'Audio'; SOURCES=ROOT/'Sources'
OUT.mkdir(parents=True,exist_ok=True); SOURCES.mkdir(parents=True,exist_ok=True)
SR=48000
RNG=np.random.default_rng(91112)
raw={}; records=[]
previous=json.loads((PREVIOUS/'audio_manifest.json').read_text(encoding='utf-8'))
for source in previous['sources']:
    if source['role'] not in ('flesh','cavity','inhale'): continue
    path=SOURCES/source['file']
    if not path.exists(): shutil.copy2(PREVIOUS/'Sources'/source['file'],path)
    pcm=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error',
        '-i',str(path),'-ac','1','-ar',str(SR),'-f','f32le','pipe:1'],check=True,capture_output=True).stdout
    raw[source['role']]=np.frombuffer(pcm,dtype='<f4').astype(np.float64)
    item=dict(source); item['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    item['reuse']='CreatureAudioV10 retained CC0 HQ MP3 preview source'
    records.append(item)

def clock(d): return np.arange(round(d*SR))/SR
def unit(x): return x/max(1.e-9,float(np.max(np.abs(x))))
def band(x,lo,hi): return sosfilt(butter(3,[lo,hi],btype='bandpass',fs=SR,output='sos'),x)
def fade(x,attack=.004,release=.04):
    t=np.arange(len(x))/SR
    return x*np.clip(t/attack,0.,1.)*np.clip((len(x)/SR-t)/release,0.,1.)
def tissue(role,start,d,lo,hi,rate=1.):
    positions=(start+clock(d)*rate)*SR
    return unit(fade(band(np.interp(positions,np.arange(len(raw[role])),raw[role],left=0.,right=0.),lo,hi)))
def air(d,lo,hi): return unit(band(RNG.normal(0.,1.,len(clock(d))),lo,hi))
def thump(d,hz):
    t=clock(d)
    return fade((np.sin(2*np.pi*hz*t)+.24*np.sin(2*np.pi*hz*1.79*t))*np.exp(-t*24.),.002,.03)

manifest=dict(revision='StepsHurtV11',monster='鼓囊 M-09',sample_rate=SR,channels=1,
    sources=records,base_creature_gain='preserve existing Blueprint setting (V10 1.35)',
    format='16-bit mono PCM WAV derived from retained lossy previews and original synthesis',
    listened=False,runtime_tested=False,clips={})
def save(role,x,peak,description):
    x=fade(x-np.mean(x),.002,.035)
    x=unit(np.tanh(unit(x)*1.45))*10**(peak/20.)
    name='S_Bellow_'+role+'.wav'
    with wave.open(str(OUT/name),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(SR)
        f.writeframes(np.rint(x*32767.).astype('<i2').tobytes())
    manifest['clips'][role]=dict(file=name,duration=len(x)/SR,looping=False,
        peak_ceiling_dbfs=peak,description=description)

for role,at,d,hz in [('FootstepA',20.45,.24,64.),('FootstepB',21.08,.26,71.),
                     ('FootstepC',22.20,.25,59.),('FootstepD',24.16,.28,76.)]:
    t=clock(d)
    x=thump(d,hz)*.56
    x+=tissue('flesh',at,d,120.,4300.)*.39*np.exp(-t*4.)
    x+=air(d,180.,3900.)*.16*np.exp(-t*35.)
    x+=tissue('cavity',9.+at*.1,d,90.,650.)*.055
    save(role,x,-5.,'Short weight-bearing wet pad with a restrained tissue tail; gait touchdown, no shoe/metal click')

for role,at,d,rate in [('HurtA',.21,.27,.88),('HurtB',.62,.31,.92),('HurtC',.95,.34,.84)]:
    t=clock(d)
    x=tissue('inhale',at,d,140.,3900.,rate)*.60*np.exp(-t*1.3)
    x+=tissue('flesh',20.5+at,d,130.,4600.)*.26*np.exp(-t*5.)
    x+=tissue('cavity',12.+at,d,80.,800.)*.17
    x+=air(d,440.,3000.)*.09*np.exp(-t*12.)
    x+=thump(d,84.)*.10
    save(role,x,-4.,'Constricted throat/sac rasp and short wet hit; actual nonfatal damage only')

(ROOT/'audio_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(SOURCES/'README.md').write_text('Reused CC0 raw ingredients from ../.. / CreatureAudioV10.\n'
    'Inputs are retained HQ MP3 previews, not original lossless masters. See ../audio_manifest.json for provenance.\n',encoding='utf-8')
print('BELLOW_STEPS_HURT_V11_AUTHORED: 4 footsteps and 3 hurt cues; no playback.',flush=True)
