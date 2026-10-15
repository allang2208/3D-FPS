"""Produce a short original low air-intake cue; no audition."""
from pathlib import Path
import numpy as np
from scipy.signal import butter,sosfilt
import wave,json
ROOT=Path(__file__).resolve().parent;rate=48000;seconds=1.2;t=np.arange(round(rate*seconds))/rate
rng=np.random.default_rng(6617);noise=rng.normal(size=len(t))
air=sosfilt(butter(3,[120,1350],btype='bandpass',fs=rate,output='sos'),noise)
low=sosfilt(butter(3,[45,250],btype='bandpass',fs=rate,output='sos'),rng.normal(size=len(t)))
envelope=np.minimum(t/.22,1)**1.4*np.minimum((seconds-t)/.10,1)*(.28+.72*(t/seconds)**1.3)
pulse=.85+.15*np.sin(2*np.pi*(6*t+2*t*t))
signal=(air*.75+low*.70+np.sin(2*np.pi*(64*t+8*t*t))*.035)*envelope*pulse
signal*=.58/max(.001,np.max(np.abs(signal)));path=ROOT/'Export/M66_furnace_inhale.wav'
with wave.open(str(path),'wb') as out:
    out.setnchannels(1);out.setsampwidth(2);out.setframerate(rate);out.writeframes((signal*32767).astype('<i2').tobytes())
(ROOT/'Records/inhale_authoring.json').write_text(json.dumps({'file':str(path),'seconds':seconds,'sample_rate':rate,'source':'original filtered air/noise synthesis','auditioned':False},indent=2))
print('M66_INHALE_AUTHORED '+str(path))
