"""Local reference mix excerpts, cleaned and aligned to RSH action contacts.
These are derivatives of the supplied video mix, not isolated licensed stems.
No playback or listening/acceptance test is run by this script.
"""
from pathlib import Path
import json, hashlib
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt, stft, istft

O=Path(__file__).parent
src=O/'Reference/reference_0_22.wav'
rate,data=wavfile.read(src)
data=data.astype(np.float64)
if data.ndim==1:data=data[:,None]
out=O/'Audio';out.mkdir(exist_ok=True)
cuts=[('Fire',20.425,21.145,0.,75),('Open',15.66,15.93,.47,420),
      ('Eject',16.49,16.87,1.10,500),('Retrieve',17.64,17.96,2.12,400),
      ('Insert',17.99,18.32,2.62,300),('Release',18.37,18.55,2.90,500),
      ('Withdraw',18.52,18.74,3.17,500),('Close',18.78,19.10,3.70,350)]
noise=data[int(19.75*rate):int(20.04*rate)]
receipt=dict(reference='https://www.bilibili.com/video/BV1vh4HejEUF/',range_seconds=[0,22],
    source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),
    provenance='User-selected MWIII video mixed audio; local reference derivatives only; redistribution rights not established',
    sample_rate=rate,channels=data.shape[1],listened=False,runtime_tested=False,clips=[])
for name,begin,end,contact,hp in cuts:
    x=data[round(begin*rate):round(end*rate)].copy()
    sos=butter(3,hp,btype='highpass',fs=rate,output='sos')
    x=sosfilt(sos,x,axis=0)
    cleaned=[]
    for c in range(x.shape[1]):
        _,_,n=stft(sosfilt(sos,noise[:,c]),rate,nperseg=512,noverlap=384)
        floor=np.median(abs(n),axis=1)
        _,_,z=stft(x[:,c],rate,nperseg=512,noverlap=384)
        mag=abs(z);gain=np.maximum(.13,1-1.65*floor[:,None]/np.maximum(mag,1e-9))
        _,y=istft(z*gain,rate,nperseg=512,noverlap=384)
        cleaned.append(y[:len(x)])
    x=np.stack(cleaned,axis=1)
    # Keep the attack; locate only silence/pre-roll before it, not peak tail energy.
    hop=48
    env=np.sqrt((x[:len(x)//hop*hop].reshape(-1,hop,x.shape[1])**2).mean(axis=(1,2)))
    threshold=max(.004,float(env.max())*.12)
    onset=max(0,int(np.argmax(env>threshold)*hop)-round(.0015*rate))
    x=x[onset:]
    peak=float(np.max(np.abs(x)))
    target=10**((-2 if name=='Fire' else -8)/20)
    gain=min(3.,target/max(peak,1e-8));x*=gain
    fade=min(round(.003*rate),len(x)//4);tail=min(round((.10 if name=='Fire' else .018)*rate),len(x)//4)
    x[:fade]*=np.linspace(0,1,fade)[:,None];x[-tail:]*=np.linspace(1,0,tail)[:,None]
    path=out/('S_RSH12_'+name+'.wav')
    wavfile.write(path,rate,np.round(np.clip(x,-1,1)*32767).astype(np.int16))
    receipt['clips'].append(dict(name=name,file=path.name,cut=[begin,end],trim_seconds=onset/rate,
        contact_source_seconds=contact,highpass_hz=hp,gain=gain,duration=len(x)/rate,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
(out/'manifest.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
print('RSH12_AUDIO_AUTHORED',len(receipt['clips']))
