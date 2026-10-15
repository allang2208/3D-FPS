"""Original charge/flight audio and a separate actual-contact ground impact."""
from pathlib import Path
import json,wave
import numpy as np
from scipy.signal import butter,sosfilt
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HeQueBoss20261014/JumpSlamV02');sr=48000
def noise(n,seed,lo,hi):
    return sosfilt(butter(3,[lo,hi],btype='bandpass',fs=sr,output='sos'),np.random.default_rng(seed).normal(size=n))
def save(name,y,peak=.80):
    y=np.tanh(y);y*=peak/max(1e-8,np.max(np.abs(y)))
    with wave.open(str(ROOT/'Audio'/name),'wb') as f:
        f.setparams((1,2,sr,len(y),'NONE','not compressed'));f.writeframes((y*32767).astype('<i2').tobytes())
t=np.arange(round(1.95*sr))/sr
envelope=np.clip(t/.35,0,1)*np.clip((1.95-t)/.08,0,1)*(.16+.84*np.clip(t/1.80,0,1)**1.4)
charge=envelope*(.24*noise(len(t),15171,65,850)+.075*np.sin(2*np.pi*(48*t+3*t*t)))
save('S_HeQue_JumpChargeV02.wav',charge,.56)
t=np.arange(sr)/sr
air=noise(len(t),15172,120,2200)
y=np.exp(-t*13)*(.34*np.sin(2*np.pi*64*t)+.75*air)
age=np.maximum(t-.5,0);y+=(t>=.5)*(1.2*air+.25*np.sin(2*np.pi*(100*age-35*age*age)))*np.exp(-age*12)
save('S_HeQue_JumpAirV02.wav',y,.72)
t=np.arange(round(2.6*sr))/sr
low=noise(len(t),15173,25,200);grit=noise(len(t),15174,350,3800)
impact=.95*np.sin(2*np.pi*(36*t+2.8*(1-np.exp(-t*40))))*np.exp(-t*6)
impact+=2.7*low*np.exp(-t*6)+1.15*grit*np.exp(-t*40)
# Contact crack and a delayed mass-settle match compression and rebound.
impact+=.32*noise(len(t),15176,1500,6500)*np.exp(-t*65)
settle=np.maximum(t-.067,0)
impact+=(t>=.067)*.38*np.sin(2*np.pi*48*settle)*np.exp(-settle*17)
for start,gain in ((.14,.15),(.32,.085),(.58,.045)):
    a=np.maximum(t-start,0)
    impact+=(t>=start)*gain*(np.sin(2*np.pi*713*a)+.4*np.sin(2*np.pi*1203*a))*np.exp(-a*18)
recover=np.clip((t-.70)/.3,0,1)*np.clip((2.4-t)/.8,0,1)
impact+=recover*.10*noise(len(t),15175,70,700)
save('S_HeQue_JumpImpactV02.wav',impact,.86)
(ROOT/'Records/audio.json').write_text(json.dumps(dict(source='original synthesis',sample_rate=sr,charge_seconds=1.95,air_seconds=1.,
    dive_audio_seek=.5,impact_seconds=2.6,impact_trigger='actual replicated landing',auditioned=False),indent=2),encoding='utf8')
print('HEQUE_JUMP_AUDIO_AUTHORED',flush=True)
