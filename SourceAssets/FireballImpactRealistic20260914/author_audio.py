"""Produce editable pressure/combustion/embers stems from the existing fireball cue."""
import json, wave
from pathlib import Path
import numpy as np

root=Path(__file__).resolve().parent
source=root.parent/'Fireball20260914/fireball_hit.wav'
with wave.open(str(source),'rb') as reader:
    rate=reader.getframerate(); channels=reader.getnchannels()
    if reader.getsampwidth()!=2: raise RuntimeError('Expected the existing PCM16 authoring source')
    original=np.frombuffer(reader.readframes(reader.getnframes()),'<i2').astype(np.float64)/32768
    original=original.reshape(-1,channels).mean(axis=1)
length=int(rate*1.25);t=np.arange(length)/rate
base=np.zeros(length);base[:min(length,len(original))]=original[:length]
rng=np.random.default_rng(9142026)

def band(signal,lo,hi):
    frequencies=np.fft.rfftfreq(len(signal),1/rate)
    response=1/(1+(frequencies/hi)**6)
    if lo: response*=1-1/(1+(frequencies/lo)**6)
    return np.fft.irfft(np.fft.rfft(signal)*response,n=len(signal))

def normalize(signal):
    return signal/max(np.max(np.abs(signal)),1e-9)

attack=1-np.exp(-t*700)
pressure=normalize(band(base,35,210))*.48*attack*np.exp(-t*10)
pressure+=.11*np.sin(2*np.pi*(83*t-16*t*t))*attack*np.exp(-t*17)
combustion=normalize(band(base,180,6500))*.62*attack*np.exp(-t*2.8)
gas=normalize(band(rng.normal(size=length),170,2900))
combustion+=gas*.16*attack*np.exp(-t*9)
embers=np.zeros(length)
for when in rng.uniform(.14,.80,14):
    dt=t-when
    envelope=np.where(dt>=0,(1-np.exp(-np.maximum(dt,0)*2400))*np.exp(-np.maximum(dt,0)*rng.uniform(130,220)),0)
    grain=normalize(band(rng.normal(size=length),1200,7800))
    embers+=grain*envelope*rng.uniform(.016,.037)
fade=np.minimum(1,np.maximum(0,(1.23-t)/.1))
mix=np.tanh((pressure+combustion+embers)*1.15)*fade
gain=.79/max(np.max(np.abs(mix)),1e-9)

def write(name,signal):
    with wave.open(str(root/name),'wb') as writer:
        writer.setnchannels(1);writer.setsampwidth(2);writer.setframerate(rate)
        writer.writeframes((np.clip(signal,-.99,.99)*32767).astype('<i2').tobytes())

for name,signal in [('Pressure.wav',pressure),('Combustion.wav',combustion),('Embers.wav',embers)]:write(name,signal)
write('FireballImpactLayered.wav',mix*gain)
(root/'audio-source.json').write_text(json.dumps({'source':str(source),'sample_rate':rate,'duration_seconds':1.25,
    'layers':['Filtered original impact and short low pressure transient','Filtered original combustion with short gas noise','Sparse original procedural crackle'],
    'mix':'Single mono spatial sound at runtime; editable stems retained; peak -2.05 dBFS',
    'license':'Existing project cue and project-authored DSP layers; keep original source rights, no public redistribution',
    'status':'Offline audio production; not auditioned in game'},indent=2),encoding='utf-8')
print('FIREBALL_IMPACT_AUDIO_AUTHORED',flush=True)
