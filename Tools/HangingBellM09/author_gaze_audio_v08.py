"""Original close eye flutter, rising focus tone and soft discharge; no samples."""
import numpy as np, wave, json
from scipy.signal import butter,sosfilt
from pathlib import Path
out=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003/GazeV08')
for d in ('Audio','Records'):(out/d).mkdir(parents=True,exist_ok=True)
sr=48000;t=np.arange(3*sr)/sr;rng=np.random.default_rng(908)
n=rng.normal(0,1,len(t))
def band(a,b):return sosfilt(butter(3,[a,b],btype='bandpass',fs=sr,output='sos'),n)
def smooth(x):
 x=np.clip(x,0,1);return x*x*(3-2*x)
soft=band(220,1400);air=band(1500,4800)
charge=smooth(t/.8)*(1-smooth((t-1.19)/.09))
y=.095*charge*(np.sin(2*np.pi*(105*t+49*t*t))+.36*np.sin(2*np.pi*(209*t+85*t*t)))
y+=.09*charge*soft
for a in (.08,.14,.20,.26,.32):
 age=np.maximum(t-a,0);y+=(t>=a)*.035*soft*(1-np.exp(-age*150))*np.exp(-age*16)
fire=smooth((t-1.25)/.025)*(1-smooth((t-1.72)/.13))
y+=fire*(.13*soft+.042*air+.14*np.sin(2*np.pi*183*t)+.048*np.sin(2*np.pi*281*t))
for a in (1.25,1.45,1.65):
 age=np.maximum(t-a,0);y+=(t>=a)*.05*soft*(1-np.exp(-age*300))*np.exp(-age*22)
tail=smooth((t-1.85)/.03)*(1-smooth((t-1.9)/.62))
y+=tail*(.045*soft+.035*np.sin(2*np.pi*(143*t-8*t*t)))
y*=smooth(t/.012)*(1-smooth((t-2.82)/.18));y-=y.mean();y*=.70/max(.70,float(np.abs(y).max()))
path=out/'Audio/S_M09_Gaze_V08.wav'
with wave.open(str(path),'wb') as f:
 f.setnchannels(1);f.setsampwidth(2);f.setframerate(sr);f.writeframes((32767*y).astype('<i2').tobytes())
(out/'Records/audio_source.json').write_text(json.dumps({'file':str(path),'duration':3,'sample_rate':sr,
 'provenance':'Original procedural synthesis; no third-party samples','tested':False},indent=2),encoding='utf8')
print('M09_GAZE_AUDIO_SAVED')
