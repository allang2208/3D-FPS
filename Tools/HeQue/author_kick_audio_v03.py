"""Original body strain, accelerating air displacement and heavy recovery footfall."""
import json,wave
from pathlib import Path
import numpy as np
from scipy.signal import butter,sosfilt
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HeQueBoss20261014/SideCrushV03');(ROOT/'Audio').mkdir(parents=True,exist_ok=True)
sr=48000;t=np.arange(round(3.6*sr))/sr;rng=np.random.default_rng(151503)
noise=rng.normal(size=len(t));y=np.zeros_like(t)
def band(lo,hi):return sosfilt(butter(3,[lo,hi],btype='bandpass',fs=sr,output='sos'),noise)
strain=band(85,650);air=band(180,1900);crack=band(1100,4800);low=band(35,200)
load=np.clip((t-.36)/.7,0,1)*np.clip((1.48-t)/.15,0,1)
y+=load*.16*strain
u=np.clip((t-1.48)/.15,0,1);tail=np.exp(-np.maximum(t-1.63,0)*22)
y+=(t>=1.48)*u**2.8*tail*(1.5*air+.35*crack)
for start,gain in ((.33,.22),(1.635,.52),(3.165,1.0)):
    age=np.maximum(t-start,0);on=t>=start
    thump=np.sin(2*np.pi*(44*age+2.0*(1-np.exp(-age*20))))
    y+=on*gain*(.45*thump*np.exp(-age*14)+1.8*low*np.exp(-age*15)+.12*crack*np.exp(-age*55))
for start,gain in ((1.79,.06),(1.97,.04),(2.18,.02),(3.24,.04)):
    age=np.maximum(t-start,0)
    y+=(t>=start)*gain*(np.sin(2*np.pi*721*age)+.5*np.sin(2*np.pi*1381*age))*np.exp(-age*30)
y=np.tanh(y*1.3);y*=.82/max(1e-8,np.max(np.abs(y)))
with wave.open(str(ROOT/'Audio/S_HeQue_ForwardKickImpactV03.wav'),'wb') as f:
    f.setparams((1,2,sr,len(y),'NONE','not compressed'));f.writeframes((y*32767).astype('<i2').tobytes())
(ROOT/'Records/audio.json').write_text(json.dumps(dict(source='original synthesis',duration=3.6,release=[1.48,1.66],
    extension_accent=1.635,landing=3.165,auditioned=False),indent=2),encoding='utf8')
print('HEQUE_KICK_AUDIO_AUTHORED')
