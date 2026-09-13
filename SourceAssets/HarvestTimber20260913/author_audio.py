"""Original synthesized wood fracture and timber landing sounds; no third-party samples."""
from pathlib import Path
import wave
import numpy as np
ROOT=Path(__file__).parent/'Delivery';ROOT.mkdir(exist_ok=True)
SR=44100
rng=np.random.default_rng(913180)
def burst(out,start,duration,frequency,amplitude):
    n=int(duration*SR);t=np.arange(n)/SR
    noise=rng.standard_normal(n)
    signal=(.55*np.sin(2*np.pi*frequency*t)+.25*np.sin(2*np.pi*frequency*1.57*t)+.2*noise)*np.exp(-t/duration*7)
    i=int(start*SR);out[i:i+n]+=signal[:len(out[i:i+n])]*amplitude
def save(name,data):
    data=np.tanh(data);data*=.83/max(.83,np.max(np.abs(data)))
    with wave.open(str(ROOT/(name+'.wav')),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(SR);f.writeframes((data*32767).astype('<i2').tobytes())
crack=np.zeros(int(SR*.85))
for i in range(11):burst(crack,.025+i*.037,.075+i*.008,630-i*31,.08+i*.022)
burst(crack,.4,.38,145,.36);save('S_TreeCrack',crack)
landing=np.zeros(int(SR*1.6))
for start,freq,amp,dur in [(0,54,.75,.65),(.025,102,.45,.42),(.13,176,.24,.3),(.32,81,.17,.3)]:burst(landing,start,dur,freq,amp)
for i in range(20):burst(landing,.2+i*.045,.1,850+i*67,.035*(1-i/22))
save('S_TreeLanding',landing)
print('Original procedural timber WAV files authored.')
