"""Original charge/flight audio and a separate actual-contact ground impact."""
from pathlib import Path
import json,wave
import numpy as np
from scipy.signal import butter,sosfilt
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HeQueBoss20261014/JumpSlamV01');sr=48000
def noise(n,seed,lo,hi):
    return sosfilt(butter(3,[lo,hi],btype='bandpass',fs=sr,output='sos'),np.random.default_rng(seed).normal(size=n))
def save(name,y,peak=.80):
    y=np.tanh(y);y*=peak/max(1e-8,np.max(np.abs(y)))
    with wave.open(str(ROOT/'Audio'/name),'wb') as f:
        f.setparams((1,2,sr,len(y),'NONE','not compressed'));f.writeframes((y*32767).astype('<i2').tobytes())
t=np.arange(round(1.5*sr))/sr
envelope=np.clip(t/.25,0,1)*np.clip((1.5-t)/.10,0,1)*(.2+.8*np.clip(t/1.30,0,1))
charge=envelope*(.20*noise(len(t),15171,80,950)+.055*np.sin(2*np.pi*(58*t+5*t*t)))
save('S_HeQue_JumpChargeV01.wav',charge,.52)
t=np.arange(sr)/sr
air=noise(len(t),15172,120,2200)
y=np.exp(-t*13)*(.34*np.sin(2*np.pi*64*t)+.75*air)
age=np.maximum(t-.5,0);y+=(t>=.5)*(.85*air+.18*np.sin(2*np.pi*(85*age-20*age*age)))*np.exp(-age*7)
save('S_HeQue_JumpAirV01.wav',y,.65)
t=np.arange(round(2.6*sr))/sr
low=noise(len(t),15173,25,200);grit=noise(len(t),15174,350,3800)
impact=.75*np.sin(2*np.pi*(34*t+2.4*(1-np.exp(-t*30))))*np.exp(-t*8)
impact+=2.5*low*np.exp(-t*8)+.70*grit*np.exp(-t*22)
for start,gain in ((.12,.12),(.27,.07),(.48,.04)):
    a=np.maximum(t-start,0)
    impact+=(t>=start)*gain*(np.sin(2*np.pi*713*a)+.4*np.sin(2*np.pi*1203*a))*np.exp(-a*18)
recover=np.clip((t-.70)/.3,0,1)*np.clip((2.4-t)/.8,0,1)
impact+=recover*.10*noise(len(t),15175,70,700)
save('S_HeQue_JumpImpactV01.wav',impact)
(ROOT/'Records/audio.json').write_text(json.dumps(dict(source='original synthesis',sample_rate=sr,charge_seconds=1.5,air_seconds=1.,
    dive_audio_seek=.5,impact_seconds=2.6,impact_trigger='actual replicated landing',auditioned=False),indent=2),encoding='utf8')
print('HEQUE_JUMP_AUDIO_AUTHORED',flush=True)
