"""Original pneumatic two-note warning and two pressure releases. No audition."""
from pathlib import Path
import wave,json
import numpy as np
from scipy.signal import butter,sosfilt
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HeQueBoss20261014/RiftPressureV01');(ROOT/'Audio').mkdir(parents=True,exist_ok=True)
sr=48000;t=np.arange(round(4.3*sr))/sr;rng=np.random.default_rng(141015);noise=rng.normal(size=len(t))
def band(lo,hi):return sosfilt(butter(3,[lo,hi],btype='bandpass',fs=sr,output='sos'),noise)
air=band(350,2300);crack=band(900,5800);low=band(35,230);y=np.zeros_like(t)
for start,end,base,rise,gain in ((.15,.69,145,200,.44),(.79,1.39,250,330,.57)):
    age=np.clip(t-start,0,end-start);u=age/(end-start)
    env=np.clip((t-start)/.06,0,1)*np.clip((end-t)/.09,0,1)*(.4+.6*u)
    phase=2*np.pi*(base*age+.5*rise/(end-start)*age**2)
    reed=np.sin(phase)+.23*np.sin(phase*2.03)+.10*np.sin(phase*3.11)
    y+=gain*env*(.26*reed+.42*air+.12*low)
for release,gain in ((1.55,1.),(2.15,1.13)):
    age=np.maximum(t-release,0);on=t>=release
    sub=np.sin(2*np.pi*(54*age+2.6*(1-np.exp(-age*16))))
    y+=on*gain*(.48*sub*np.exp(-age*10)+.28*crack*np.exp(-age*36)+.55*air*np.exp(-age*6))
y=np.tanh(y*1.15);y*=.78/max(1e-8,np.max(np.abs(y)))
path=ROOT/'Audio/S_HeQue_RiftPressure.wav'
with wave.open(str(path),'wb') as f:f.setparams((1,2,sr,len(y),'NONE','not compressed'));f.writeframes((y*32767).astype('<i2').tobytes())
(ROOT/'Records/audio.json').write_text(json.dumps(dict(source='original synthesis',sample_rate=sr,duration=4.3,warning_notes=[[.15,.69],[.79,1.39]],releases=[1.55,2.15],auditioned=False),indent=2),encoding='utf8')
print('HEQUE_RIFT_AUDIO_AUTHORED')
