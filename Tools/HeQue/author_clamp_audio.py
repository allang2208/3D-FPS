"""Original heavy tissue compression, brace and cuff-chain tail. No audition."""
from pathlib import Path
import json,wave
import numpy as np
from scipy.signal import butter,sosfilt
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HeQueBoss20261014/HeavyClampV01')
(ROOT/'Audio').mkdir(parents=True,exist_ok=True)
sr=48000;t=np.arange(round(4.2*sr))/sr;rng=np.random.default_rng(151015)
noise=rng.normal(size=len(t));y=np.zeros_like(t)
def band(lo,hi):return sosfilt(butter(3,[lo,hi],btype='bandpass',fs=sr,output='sos'),noise)
body=band(40,260);scrape=band(120,850);crack=band(600,3600)
# A quiet drawn-out strain, stopped by a blunt double compression, not a voice.
load=np.clip((t-.28)/1.02,0,1)*np.clip((1.52-t)/.10,0,1)
y+=load*(.14*scrape+.035*np.sin(2*np.pi*(64*t+7*t*t)))
for start,gain in ((.26,.30),(1.67,1.),(1.79,.46)):
    age=np.maximum(t-start,0);on=t>=start
    thud=np.sin(2*np.pi*(43*age+2.2*(1-np.exp(-16*age))))
    y+=on*gain*(.48*thud*np.exp(-age*10)+1.5*body*np.exp(-age*13)+.27*crack*np.exp(-age*42))
# Small rigid-link clinks trail the body stop, and scrape during reopening.
for start,gain in ((1.87,.11),(2.04,.07),(2.30,.04),(2.92,.045),(3.19,.035)):
    age=np.maximum(t-start,0);on=t>=start
    metal=sum(np.sin(2*np.pi*f*age)*np.exp(-age*d) for f,d in ((733,25),(1193,31),(2017,46)))
    y+=on*gain*metal
recover=np.clip((t-2.55)/.3,0,1)*np.clip((3.65-t)/.35,0,1)
y+=recover*.14*scrape
y=np.tanh(y*1.25);y*=.80/max(1e-8,np.max(np.abs(y)))
with wave.open(str(ROOT/'Audio/S_HeQue_HeavyClamp.wav'),'wb') as f:
    f.setparams((1,2,sr,len(y),'NONE','not compressed'));f.writeframes((y*32767).astype('<i2').tobytes())
(ROOT/'Records/audio.json').write_text(json.dumps(dict(source='original synthesis',sample_rate=sr,duration=4.2,
    brace=.26,compression=1.67,settle=1.79,chain_tail=[1.87,2.04,2.30],auditioned=False),indent=2),encoding='utf8')
print('HEQUE_CLAMP_AUDIO_AUTHORED')
