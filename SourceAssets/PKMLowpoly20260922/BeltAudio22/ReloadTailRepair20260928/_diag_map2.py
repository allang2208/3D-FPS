import numpy as np, soundfile as sf
from pathlib import Path
from scipy.signal import butter, sosfiltfilt
P = Path(r"D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922\BeltAudio22")
RATE=48000
x,_ = sf.read(P/"reference_audio.wav")
mono = x if x.ndim==1 else x.mean(axis=1)
mono = sosfiltfilt(butter(2,80,fs=RATE,btype="highpass",output="sos"), mono)
step=round(0.25*RATE)
print("coarse 0.25 s RMS dBFS, 16.0-27.0 s")
for i in range(int(16.0/0.25), int(27.0/0.25)):
    seg=mono[i*step:(i+1)*step]
    db=20*np.log10(np.sqrt(np.mean(seg**2))+1e-30)
    print(f"{i*0.25:6.2f}  {db:7.1f}  " + "#"*max(0,int((db+70)*1.2)))
