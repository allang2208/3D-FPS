"""Resonance V09: concussive membrane blast. V07 read as soft chimes; V09 keeps
the pulse timing contract (charge 1.1s + six pulses at 1.1/1.8/2.5/3.2/3.9/4.6)
but rebuilds every layer as a pressure attack: sub thump, crack transient,
dark inharmonic bell, and an expanding-ring whoosh per pulse. All synthesized."""
import numpy as np, wave, json
from scipy.signal import butter, sosfilt, sosfiltfilt
from pathlib import Path
out=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003/ResonanceV09')
(out/'Audio').mkdir(parents=True,exist_ok=True);(out/'Records').mkdir(exist_ok=True)
sr=48000;t=np.arange(round(5.8*sr))/sr;rng=np.random.default_rng(909)
noise=rng.normal(0,1,len(t))
def band(lo,hi,src=noise,order=3):
    return sosfilt(butter(order,[lo,hi],btype='bandpass',fs=sr,output='sos'),src)

rumble=band(38,300)
shimmer=band(900,5200)
y=np.zeros_like(t)

# --- Charge 0 -> 1.1s: pressure swell, infrasonic rise, membrane tightening ---
charge=np.clip(t/1.05,0,1)**1.6*np.clip((1.14-t)/.18,0,1)
infra=np.sin(2*np.pi*(38*t+24*t*t))                       # 38 -> ~90 Hz rising
y+=charge*(.30*infra+.17*rumble+.05*shimmer)
# stretched-skin groan: detuned high partial climbing into the snap
groan=np.sin(2*np.pi*(640*t+210*t*t))+.55*np.sin(2*np.pi*(917*t+160*t*t)+1.1)
y+=charge*.05*groan*(0.4+0.6*np.clip(t/1.0,0,1))
# intake hiss right before first pulse
y+=.10*shimmer*np.exp(-((t-1.06)/.045)**2)

# --- Six pulses, escalating ---
pulse_times=(1.1,1.8,2.5,3.2,3.9,4.6)
fund=(62,68,75,82,90,98)
for i,(pulse,hz) in enumerate(zip(pulse_times,fund)):
    age=np.maximum(t-pulse,0);on=(t>=pulse)
    scale=1.0+i*0.09
    # sub thump: fast pitch drop, felt more than heard
    sub=np.sin(2*np.pi*(hz*.72*age*np.exp(-age*3.2)+hz*.52*age))
    y+=on*scale*.55*sub*np.exp(-age*9.0)
    # crack transient: 25ms broadband snap riding the pulse front
    crack=np.exp(-age*70)
    y+=on*scale*(.24*band(1500,7000)*crack)
    # dark inharmonic bell body: keeps the bell identity without reading chime
    body=np.zeros_like(t)
    for ratio,gain,decay in ((1,.34,3.6),(1.58,.20,5.0),(2.55,.10,6.8),(3.92,.05,9.5)):
        phase=2*np.pi*(hz*ratio*age+hz*ratio*.05*.04*(1-np.exp(-age/.04)))
        body+=gain*np.sin(phase)*np.exp(-age*decay)
    # slight beat: a detuned partner 0.7% up, dies fast
    body+=.11*np.sin(2*np.pi*hz*1.007*age)*np.exp(-age*5.5)
    y+=on*scale*body
    # expanding ring whoosh: noise rising 250->1400Hz over the visible wave front
    wn=band(250,1400)
    ring=np.exp(-age*7.5)
    y+=on*scale*.16*wn*ring*np.sin(2*np.pi*(2.2*age))
    # pressure tail boom
    y+=on*scale*.20*np.sin(2*np.pi*44*age)*np.exp(-age*4.5)

y=np.tanh(y*1.15)                      # soft-clip cohesion / aggression
y*=np.clip(t/.006,0,1)*np.clip((5.8-t)/.12,0,1)
y-=np.mean(y);y*=.82/max(.82,float(np.max(np.abs(y))))
f=out/'Audio/S_M09_Resonance_V09.wav'
with wave.open(str(f),'wb') as w:
    w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes((y*32767).astype('<i2').tobytes())
(out/'Records/audio_source.json').write_text(json.dumps({'file':str(f),'sample_rate':sr,'duration':5.8,
 'pulses':list(pulse_times),'fundamentals_hz':list(fund),
 'design':'concussive pressure attack: sub thump + crack + dark inharmonic bell + ring whoosh; replaces V07 chimes',
 'provenance':'Original local procedural synthesis; no sampled third-party audio',
 'tested':False},indent=2),encoding='utf8')
print('M09_RESONANCE_V09_AUDIO_SAVED peak=%.3f'%float(np.max(np.abs(y))))
