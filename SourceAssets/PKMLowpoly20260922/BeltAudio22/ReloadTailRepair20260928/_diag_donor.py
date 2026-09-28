import numpy as np, soundfile as sf
from pathlib import Path
from scipy.signal import butter, sosfiltfilt, stft
P = Path(r"D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922\BeltAudio22")
RATE=48000; NP,HOP=2048,512
x,_ = sf.read(P/"reference_audio.wav"); mono = x.mean(axis=1) if x.ndim>1 else x
mono_hp = sosfiltfilt(butter(2,80,fs=RATE,btype="highpass",output="sos"), mono)
BW=[(1.10,3.25),(3.90,5.00),(6.10,7.25),(7.65,8.75),(9.05,10.00)]
def F(sig):
    _,_,Z=stft(sig,fs=RATE,nperseg=NP,noverlap=NP-HOP,window="hann",boundary="zeros",padded=True)
    return 10*np.log10(np.sum(np.abs(Z)**2,axis=0)+1e-30)
for label,sig in (("no HP",mono),("80Hz HP",mono_hp)):
    Ps=[np.abs(stft(sig[round(a*RATE):round(b*RATE)],fs=RATE,nperseg=NP,noverlap=NP-HOP,window="hann",boundary="zeros",padded=True)[2])**2 for a,b in BW]
    bed=float(10*np.log10(np.sum(np.percentile(np.concatenate(Ps,axis=1),70,axis=1))+1e-30))
    for a,b in [(25.010,25.215),(25.010,25.225)]:
        m=F(sig[round(a*RATE):round(b*RATE)])-bed
        print(f"{label} window {a}-{b}: bed={bed:.1f} n={len(m)} min={m.min():.1f} max={m.max():.1f} pct>=6={100*(m>=6).mean():.1f}%")
        print("   ", [f"{round(i*HOP/RATE*1000)}:{v:.1f}" for i,v in enumerate(m)])
