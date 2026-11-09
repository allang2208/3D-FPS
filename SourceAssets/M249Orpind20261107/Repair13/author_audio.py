"""Designed suppressor timbre derived from the user's installed M249 one-shot."""
import soundfile as sf,numpy as np,json,hashlib
from scipy.signal import butter,sosfilt
from pathlib import Path
r=Path(__file__).resolve().parent;src=r.parent/'FireAudio/S_M249_Fire_01.wav';x,rate=sf.read(src,always_2d=True)
body=sosfilt(butter(2,1900,'lowpass',fs=rate,output='sos'),x,axis=0)
mechanical=sosfilt(butter(2,[2300,6000],'bandpass',fs=rate,output='sos'),x,axis=0)
y=body*.83+mechanical*.17
# Preserve the original timing/pitch and a restrained mechanical tail. This is
# a designed game sound, not a new recording of a real suppressed M249.
t=np.arange(len(y))/rate;y*=np.where(t<.095,1.,np.exp(-(t-.095)*3.2))[:,None]
target=np.sqrt(np.mean(x*x))*10**(-3/20);y*=target/max(np.sqrt(np.mean(y*y)),1.e-12)
y*=min(1.,10**(-1.6/20)/max(abs(y).max(),1.e-12))
sf.write(r/'S_M249_Suppressed.wav',y,rate,subtype='PCM_16')
(r/'audio_recipe.json').write_text(json.dumps(dict(source=str(src),sha256=hashlib.sha256(src.read_bytes()).hexdigest(),rate=rate,duration=len(x)/rate,channels=x.shape[1],designed_timbre=True,auditioned=False),indent=2))
print('M249 suppressor audio authored')
