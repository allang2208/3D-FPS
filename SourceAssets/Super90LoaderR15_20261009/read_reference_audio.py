"""Decode the user recording and display its editing waveform; no game/audition."""
from pathlib import Path
import json,subprocess,hashlib
import imageio_ffmpeg
import numpy as np
from scipy.signal import find_peaks
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
O=Path(__file__).parent
source=Path('C:/Users/allan/Videos/NVIDIA/Delta Force/Delta Force 2026.10.09 - 09.55.46.01.mp4')
raw=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-i',str(source),'-map','0:a:0','-ar','48000','-ac','2','-f','f32le','pipe:1'],capture_output=True,check=True).stdout
samples=np.frombuffer(raw,dtype='<f4').reshape(-1,2)
np.save(O/'reference_audio.npy',samples)
step=240
rms=np.sqrt(np.mean(samples[:len(samples)//step*step].reshape(-1,step,2)**2,axis=(1,2)))
t=(np.arange(len(rms))+.5)*step/48000
peaks,_=find_peaks(rms,distance=5,prominence=.005)
events=[dict(seconds=float(t[i]),video_frame=float(t[i]*60),rms=float(rms[i])) for i in peaks if 2.6<t[i]<5.6]
(O/'reference_audio_source.json').write_text(json.dumps(dict(source=str(source),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),rate=48000,channels=2,duration=len(samples)/48000,peaks=events),indent=2))
fig,ax=plt.subplots(figsize=(16,4));ax.plot(t*60,rms,lw=.8);ax.set(xlim=(160,335),xlabel='Reference video frame at 60 Hz',ylabel='5 ms RMS');ax.grid(alpha=.25)
for f in [164,190,220,232,246,258,269,285,293,302,308,325]:ax.axvline(f,alpha=.3);ax.text(f,ax.get_ylim()[1]*.9,str(f),rotation=90,fontsize=8)
fig.tight_layout();fig.savefig(O/'reference_waveform.png',dpi=110)
print(json.dumps(events,indent=2))
