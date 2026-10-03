"""Original three layered membrane chimes. All elements synthesized locally."""
import numpy as np, wave, json
from scipy.signal import butter, sosfilt
from pathlib import Path
out=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003/ResonanceV06')
(out/'Audio').mkdir(parents=True,exist_ok=True);(out/'Records').mkdir(exist_ok=True)
sr=48000;t=np.arange(round(2.8*sr))/sr;rng=np.random.default_rng(906)
noise=rng.normal(0,1,len(t))
def band(lo,hi):return sosfilt(butter(3,[lo,hi],btype='bandpass',fs=sr,output='sos'),noise)
rumble=band(65,480);rustle=band(550,2400)
charge=np.clip(t/.8,0,1)**1.7*np.clip((1.1-t)/.24,0,1)
y=charge*(.13*rumble+.025*rustle+.045*np.sin(2*np.pi*(51*t+12*t*t)))
for index,(pulse,hz) in enumerate(zip((1.1,1.45,1.8),(73,91,115))):
 age=np.maximum(t-pulse,0);attack=(t>=pulse)*(1-np.exp(-age*260))
 body=np.zeros_like(t)
 for ratio,gain,decay in ((1,.25,4.8),(1.47,.16,6.4),(2.19,.075,8),(3.38,.035,12)):
  # Slight downward pitch relaxation sounds like a tensioned organic sheet.
  phase=2*np.pi*(hz*ratio*age+hz*ratio*.055*.045*(1-np.exp(-age/.045)))
  body+=gain*np.sin(phase)*np.exp(-age*decay)
 y+=attack*(body+.30*rumble*np.exp(-age*14)+.10*rustle*np.exp(-age*28))*(1+index*.06)
 # Brief intake before the snap, timed to the visible membrane compression.
 y+=.07*rustle*np.exp(-((t-(pulse-.065))/.035)**2)
y*=np.clip(t/.008,0,1)*np.clip((2.8-t)/.10,0,1)
y-=np.mean(y);y*=.78/max(.78,float(np.max(np.abs(y))))
f=out/'Audio/S_M09_Resonance_V06.wav'
with wave.open(str(f),'wb') as w:
 w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes((y*32767).astype('<i2').tobytes())
(out/'Records/audio_source.json').write_text(json.dumps({'file':str(f),'sample_rate':sr,'duration':2.8,
 'pulses':[1.1,1.45,1.8],'provenance':'Original local procedural synthesis; no sampled third-party audio',
 'tested':False},indent=2),encoding='utf8')
print('M09_RESONANCE_AUDIO_SAVED')
