"""Two distinct pneumatic shots with rising warnings and a separate contact sound."""
from pathlib import Path
import json,wave
import numpy as np
from scipy.signal import butter,sosfilt
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HeQueBoss20261014/RiftPressureV02')
(ROOT/'Audio').mkdir(parents=True,exist_ok=True);sr=48000
t=np.arange(round(4.3*sr))/sr;rng=np.random.default_rng(151502);noise=rng.normal(size=len(t));y=np.zeros_like(t)
def band(lo,hi):return sosfilt(butter(3,[lo,hi],btype='bandpass',fs=sr,output='sos'),noise)
air=band(200,2200);crack=band(900,6500);low=band(35,210)
for start,end,base,rise,gain in ((.15,.69,145,200,.35),(.79,1.39,250,330,.50)):
    age=np.clip(t-start,0,end-start);u=age/(end-start)
    env=np.clip((t-start)/.06,0,1)*np.clip((end-t)/.08,0,1)*(.35+.65*u)
    phase=2*np.pi*(base*age+.5*rise/(end-start)*age**2)
    reed=np.sin(phase)+.20*np.sin(phase*2.03)+.08*np.sin(phase*3.11)
    y+=gain*env*(.25*reed+.45*air+.12*low)
for release,gain,base in ((1.55,1.,57),(2.15,1.16,46)):
    age=np.maximum(t-release,0);on=t>=release
    sub=np.sin(2*np.pi*(base*age+3.0*(1-np.exp(-age*22))))
    # Hard pneumatic front, short dense body, then a fast clearing breath.
    y+=on*gain*(.58*sub*np.exp(-age*13)+.65*crack*np.exp(-age*52)+1.5*air*np.exp(-age*14)+1.8*low*np.exp(-age*16))
    y+=on*.09*np.sin(2*np.pi*733*age)*np.exp(-age*12)
leak=np.clip((t-2.45)/.15,0,1)*np.clip((3.6-t)/.9,0,1)
y+=leak*.11*air
def save(name,a):
    a=np.tanh(a*1.15);a*=.82/max(1e-8,np.max(np.abs(a)))
    with wave.open(str(ROOT/'Audio'/name),'wb') as f:
        f.setparams((1,2,sr,len(a),'NONE','not compressed'));f.writeframes((a*32767).astype('<i2').tobytes())
save('S_HeQue_RiftPressureV02.wav',y)
age=np.arange(round(.42*sr))/sr
impact=.45*np.sin(2*np.pi*(66*age+1.8*(1-np.exp(-age*25))))*np.exp(-age*20)
impact+=1.2*air[:len(age)]*np.exp(-age*12)+.40*crack[:len(age)]*np.exp(-age*45)
save('S_HeQue_PressureImpactV02.wav',impact)
(ROOT/'Records/audio.json').write_text(json.dumps(dict(duration=4.3,pulses=[1.55,2.15],
    warning_notes=[[.15,.69],[.79,1.39]],impact_duration=.42,source='original synthesis',auditioned=False),indent=2),encoding='utf8')
print('HEQUE_RIFT_AUDIO_V02_AUTHORED')
