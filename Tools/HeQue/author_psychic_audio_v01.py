"""Original low organic heart pulses, dissonant pressure drone and fear ear tone."""
from pathlib import Path
import json,wave
import numpy as np
from scipy.signal import butter,sosfilt
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HeQueBoss20261014/PsychicV01');sr=48000
t=np.arange(round(5.2*sr))/sr;rng=np.random.default_rng(151610);noise=rng.normal(size=len(t))
def band(lo,hi):return sosfilt(butter(3,[lo,hi],btype='bandpass',fs=sr,output='sos'),noise)
low=band(35,210);tissue=band(140,1400);haze=band(400,2200)
y=np.zeros_like(t)
charge=np.clip(t/1.45,0,1)*np.clip((3.15-t)/.45,0,1)
phase=2*np.pi*(61*t+10*t*t)
y+=charge*(.07*np.sin(phase)+.045*np.sin(phase*1.061)+.045*np.sin(phase*.741)+.12*tissue)
for start in (.28,.80,1.20):
    age=np.maximum(t-start,0);on=t>=start
    y+=on*.13*np.sin(2*np.pi*48*age)*np.exp(-age*15)
for start,gain in ((1.6,1.),(2.2,1.06),(2.8,1.12)):
    age=np.maximum(t-start,0);on=t>=start
    heart=np.sin(2*np.pi*(42*age+1.7*(1-np.exp(-age*24))))
    y+=on*gain*(.58*heart*np.exp(-age*10)+1.4*low*np.exp(-age*14)+.40*tissue*np.exp(-age*22))
    y+=on*.15*(np.sin(2*np.pi*137*age)+.45*np.sin(2*np.pi*149*age))*np.exp(-age*6)
    delayed=np.maximum(t-start-.13,0)
    y+=(t>=start+.13)*.07*np.sin(2*np.pi*733*delayed)*np.exp(-delayed*25)
drain=np.clip((t-3.05)/.2,0,1)*np.clip((4.85-t)/1.2,0,1)
y+=drain*(.055*haze+.035*np.sin(2*np.pi*51*t))
def save(name,samples,peak):
    samples=np.tanh(samples);samples*=peak/max(1e-8,np.max(np.abs(samples)))
    with wave.open(str(ROOT/'Audio'/name),'wb') as f:
        f.setparams((1,2,sr,len(samples),'NONE','not compressed'));f.writeframes((samples*32767).astype('<i2').tobytes())
save('S_HeQue_PsychicHeartV01.wav',y,.80)
v=np.arange(sr*3)/sr
envelope=np.clip(v/.12,0,1)*np.clip((3-v)/.6,0,1)*(.8+.2*np.cos(2*np.pi*.7*v))
ear=envelope*(.11*np.sin(2*np.pi*173*v)+.055*np.sin(2*np.pi*181*v)+.018*np.sin(2*np.pi*690*v))
save('S_HeQue_FearEarV01.wav',ear,.22)
(ROOT/'Records/audio.json').write_text(json.dumps(dict(source='original synthesis',duration=5.2,releases=[1.6,2.2,2.8],
    fear_feedback_seconds=3,spatial_action=True,local_ear_tone=True,auditioned=False),indent=2),encoding='utf8')
print('HEQUE_PSYCHIC_AUDIO_AUTHORED',flush=True)
