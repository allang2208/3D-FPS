"""Produce pressure-forward spatial cues with explicit mix headroom, no playback."""
import json
import wave
from pathlib import Path
import numpy as np

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BellowSacLobberMeshy20261012/PresentationV04')
ROOT.mkdir(exist_ok=True)
RATE=48000
rng=np.random.default_rng(12102026)
source=Path('D:/FPS3D/FPSGAME/SourceAssets/FireballImpactRealistic20260914/Pressure.wav')
with wave.open(str(source),'rb') as reader:
    samples=np.frombuffer(reader.readframes(reader.getnframes()),'<i2').astype(np.float64)/32768.
    source_rate=reader.getframerate()

def band(signal,lo,hi):
    freq=np.fft.rfftfreq(len(signal),1/RATE)
    response=(1/(1+(freq/hi)**6))*(1-1/(1+(freq/lo)**6))
    return np.fft.irfft(np.fft.rfft(signal)*response,n=len(signal))

def unit(signal):
    return signal/max(np.max(np.abs(signal)),1e-9)

record={'source_pressure':str(source),'sample_rate':RATE,'runtime_gain':1.25,
        'source_rights':'Existing project source; derivatives for this project, no raw redistribution.',
        'auditioned':False,'cues':{}}

def write(name,signal,loop=False):
    # Soft saturation raises the short body without letting the transient clip.
    shaped=np.tanh(signal*1.55)
    shaped=unit(shaped)*10**(-2.5/20)
    if not loop:
        fade=min(int(.025*RATE),len(shaped))
        shaped[-fade:]*=np.linspace(1,0,fade)
        shaped[:48]*=np.linspace(0,1,48)
    with wave.open(str(ROOT/(name+'.wav')),'wb') as out:
        out.setnchannels(1);out.setsampwidth(2);out.setframerate(RATE)
        out.writeframes((shaped*32767).astype('<i2').tobytes())
    record['cues'][name]={'duration':len(shaped)/RATE,'loop':loop,'peak_dbfs':-2.5,
        'early_rms_dbfs':float(20*np.log10(max(np.sqrt(np.mean(shaped[:int(.25*RATE)]**2)),1e-9)))}

t=np.arange(int(RATE*1.1))/RATE
pressure=np.interp(t,np.arange(len(samples))/source_rate,samples,left=0,right=0)
pressure=unit(pressure)
attack=1-np.exp(-t*1100)
thump=np.sin(2*np.pi*(92*t-22*t*t))*attack*np.exp(-t*12)
tear=unit(band(rng.normal(size=len(t)),550,8500))*attack*np.exp(-t*30)
gas=unit(band(rng.normal(size=len(t)),160,1900))*attack*np.exp(-t*9)
wet=np.zeros(len(t))
for when in (.012,.031,.07,.13,.22,.36,.53):
    age=np.maximum(0,t-when)
    wet+=(t>=when)*(1-np.exp(-age*2500))*np.exp(-age*65)*np.sin(2*np.pi*(530*age-430*age*age))*.13
write('S_BellowRupture',pressure*.68+thump*.48+tear*.49+gas*.35+wet)
t=np.arange(int(RATE*.65))/RATE
phase=t/.65
hiss=unit(band(rng.normal(size=len(t)),500,4800))
strain=np.sin(2*np.pi*(170*t+220*t*t))*.18
beats=.68+.32*np.sin(2*np.pi*(2*phase+3*phase*phase))**2
write('S_BellowFuse',(hiss*.60+strain)*(.25+.75*phase)*beats)
t=np.arange(int(RATE*.20))/RATE
write('S_BellowContact',(np.sin(2*np.pi*115*t)*.65+unit(band(rng.normal(size=len(t)),250,4300))*.55)
      *(1-np.exp(-t*1700))*np.exp(-t*30))
# Periodic filtered noise and integer-frequency tones make a seamless flight loop.
t=np.arange(RATE)/RATE
flight=band(rng.normal(size=len(t)),260,2400)
flight=unit(flight)*(.78+.22*np.cos(2*np.pi*t*3))+np.sin(2*np.pi*153*t)*.12
write('S_BellowFlight',flight,True)
(ROOT/'audio_manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print('BELLOW_PRESENTATION_AUDIO_V04_AUTHORED '+str(ROOT),flush=True)
