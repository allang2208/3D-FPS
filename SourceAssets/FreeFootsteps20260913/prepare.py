from pathlib import Path
import json, hashlib
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly, butter, sosfilt
root=Path(__file__).resolve().parent
out=root/'Wav';out.mkdir(exist_ok=True)
files=list((root/'steps').glob('*.ogg'))+[root/'splash1.wav',root/'splash2.wav']
manifest=[]
for p in files:
    x,rate=sf.read(p,always_2d=True)
    x=x.mean(axis=1);x=resample_poly(x,48000,rate)
    indices=np.flatnonzero(abs(x)>max(abs(x))*.025)
    x=x[max(0,indices[0]-96):min(len(x),indices[-1]+480)]
    x=sosfilt(butter(2,65,btype='highpass',fs=48000,output='sos'),x)
    x=x[:int(48000*(.65 if 'splash' in p.name else .5))]
    fade=min(960,len(x)//4);x[:48]*=np.linspace(0,1,48);x[-fade:]*=np.linspace(1,0,fade)
    x*=.48/max(abs(x))
    name='S_'+p.stem
    sf.write(out/(name+'.wav'),x,48000,subtype='PCM_16')
    manifest.append({'asset':name,'source':str(p.relative_to(root)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    if 'splash' in p.name:
        deep=sosfilt(butter(2,1600,fs=48000,output='sos'),x)
        sf.write(out/(name+'_deep.wav'),deep,48000,subtype='PCM_16')
(root/'manifest.json').write_text(json.dumps(manifest,indent=2))
print('Prepared free footstep and splash WAV assets.')
