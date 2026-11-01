"""GuanLei recall: periodic metal resonance, rotating air cuts, weighted catch.
48 kHz mono game stems and stereo audition, using project-owned/user-supplied donors.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
from scipy import signal
import soundfile as sf

P = Path(__file__).resolve().parent
PROJECT = P.parents[2]
SR = 48000
rng = np.random.default_rng(102903)
WAV = P / 'Audio'
PREVIEW = P / 'Audition'
WAV.mkdir(exist_ok=True)
PREVIEW.mkdir(exist_ok=True)
sources = []

def donor(relative):
    path = PROJECT / relative
    x, sr = sf.read(path, always_2d=True)
    x = x.mean(axis=1)
    if sr != SR:
        x = signal.resample_poly(x, SR, sr)
    sources.append({'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    return x

def eq(x, low=0, high=0):
    if low:
        x = signal.sosfilt(signal.butter(3, low, 'highpass', fs=SR, output='sos'), x)
    if high:
        x = signal.sosfilt(signal.butter(3, high, 'lowpass', fs=SR, output='sos'), x)
    return x

def peak(x, target):
    return x * target / max(1e-10, np.max(np.abs(x)))

def fade(x, attack=.005, release=.04):
    x = x.copy()
    a, b = min(len(x), int(attack*SR)), min(len(x), int(release*SR))
    x[:a] *= np.linspace(0, 1, a)**1.5
    x[-b:] *= np.linspace(1, 0, b)**1.5
    return x

def pad(x, n):
    return np.pad(x[:n], (0, max(0, n-len(x))))

def save(path, x):
    sf.write(path, x, SR, subtype='PCM_16')
    return {'file': str(path.relative_to(P)), 'seconds': len(x)/SR,
            'channels': 1 if x.ndim == 1 else x.shape[1],
            'peak_dbfs': float(20*np.log10(max(1e-10, np.max(np.abs(x))))),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

# All frequencies and modulations close over the 2-second loop. The low partials
# supply mass; irregular overtones retain metal rather than an electric motor.
n = SR*2
t = np.arange(n)/SR
hum = np.zeros(n)
for f, a in [(97.5,.60),(162.5,.43),(243.5,.29),(379,.20),(581.5,.12),(886,.055)]:
    phase = rng.uniform(0, 2*np.pi)
    hum += a*np.sin(2*np.pi*f*t+phase+.12*np.sin(2*np.pi*.5*t))
hum *= .72+.17*np.cos(2*np.pi*3*t)+.08*np.sin(2*np.pi*1.5*t)
freq = np.fft.rfftfreq(n, 1/SR)
grain = np.fft.irfft(np.fft.rfft(rng.normal(size=n))*np.exp(-((freq-650)/560)**2), n)
hum = peak(hum+peak(grain,.13), .34)

# The accepted blunt swing contributes the recognisable moving mass. Wrapping
# six overlapping passes around the loop prevents dead gaps or loop clicks.
swing = donor('SourceAssets/SteelWarhammer20261014/NormalSwingAudioV1/S_Warhammer_NormalSwing.wav')
swing = fade(eq(signal.resample(swing, int(len(swing)*1.16)), 120, 5600), .008, .06)
swing = peak(swing, 1.)
air = np.zeros(n)
for i in range(6):
    positions = (np.arange(len(swing))+int((i/3)*SR)) % n
    np.add.at(air, positions, swing*(.84+.12*np.sin(i*np.pi/3)))
bed = np.fft.irfft(np.fft.rfft(rng.normal(size=n))*((freq>130)&(freq<5200)), n)
air = peak(air+peak(bed,.10)*(.35+.65*np.sin(np.pi*3*t)**4), .54)

# A short grip strike and descending low-frequency body carry the catch; the
# metal tail is damped so the hand receives weight instead of an anvil crash.
cn = int(1.02*SR)
ct = np.arange(cn)/SR
metal = donor('SourceAssets/SurfaceImpacts20260914/Impact_Metal_0.wav')
metal = fade(eq(signal.resample(metal, int(len(metal)*1.34)), 100, 3600), .001, .08)
ground = donor('SourceAssets/SteelWarhammer20261014/GroundImpactAudioV1/S_Warhammer_GroundImpact.wav')
body = pad(fade(eq(ground[:int(.24*SR)], 35, 650), .002, .085), cn)
thump = np.sin(2*np.pi*(49*ct+52*.065*(1-np.exp(-ct/.065))))*np.exp(-ct/ .105)
thump += .26*np.sin(2*np.pi*127*ct)*np.exp(-ct/.045)
contact = eq(rng.normal(size=cn), 240, 3800)*np.exp(-ct/.018)
ring = sum(a*np.sin(2*np.pi*f*ct)*np.exp(-ct/d) for f,a,d in
           [(193,.23,.25),(317,.16,.18),(511,.09,.13),(837,.05,.10)])
catch = .50*pad(peak(metal,1),cn)+.32*peak(body,1)+.66*thump+.12*peak(contact,1)+ring
catch = peak(fade(eq(catch, 28, 7000), .0015, .18), .80)

assets = [save(WAV/'S_GuanLei_RecallMetalLoop.wav',hum),
          save(WAV/'S_GuanLei_RecallAirLoop.wav',air),
          save(WAV/'S_GuanLei_RecallCatch.wav',catch)]

def loop_at(x, duration, pitch):
    phase = np.cumsum(pitch)
    return np.interp(phase % len(x), np.arange(len(x)), x, period=len(x))

def audition(duration=1.3):
    samples = int(duration*SR)
    age = np.arange(samples)/SR
    q = age/duration
    metal_pitch = .88+.20*q
    turns = max(1, int(np.ceil(duration*2.8)))
    spin = turns*30*q*q*(1-q)**2/duration
    air_pitch = np.clip(spin/3,.72,1.45)
    # Mirror runtime progress gain, then approximate moving-source attenuation.
    approach = .38+.62*q**1.3
    m = loop_at(hum,duration,metal_pitch)*(.48+.30*q)*approach
    w = loop_at(air,duration,air_pitch)*(.42+.48*q)*approach
    flight = fade(m+w, .08, .025)
    pan = .58*(1-q)
    stereo = np.column_stack([flight*np.sqrt((1-pan)/2),flight*np.sqrt((1+pan)/2)])
    start = int(.18*SR)
    result = np.zeros((start+samples+cn+int(.15*SR),2))
    result[start:start+samples] += stereo
    result[start+samples:start+samples+cn] += catch[:,None]/np.sqrt(2)
    return result

previews = [save(PREVIEW/'GuanLei_Recall_Full.wav', audition()),
            save(PREVIEW/'GuanLei_Catch_Only.wav', np.repeat(np.pad(catch,(int(.15*SR),int(.2*SR)))[:,None],2,axis=1)/np.sqrt(2))]
manifest = {'sample_rate':SR,'assets':assets,'auditions':previews,'sources':sources,
 'design':'Low inharmonic metal resonance + periodic accepted blunt swing + short heavy grip strike.',
 'rights':'Blunt swing and ground impact are user-provided project audio, original rights retained; metal donor and new resonance/noise are project-authored synthesis. No wider redistribution rights inferred.',
 'runtime':{'metal_loop_seconds':2,'air_loop_seconds':2,'catch_onset_seconds':0,'preview_recall_seconds':1.3},
 'gameplay_tested':False}
(P/'audio_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'assets':assets,'auditions':previews},ensure_ascii=False))
