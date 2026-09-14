"""Read the user-provided audio for wind cleanup and mechanical stage editing."""
import json,shutil,hashlib
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy import signal
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
O=Path(__file__).parent;SRC=Path('D:/FPS3D/资产/715')
(O/'Original').mkdir(exist_ok=True);(O/'Analysis').mkdir(exist_ok=True)
report={};fig,axes=plt.subplots(4,1,figsize=(16,10),layout='constrained')
for row,name in enumerate(['715-fire.mp3','715-reloading.mp3']):
    p=SRC/name;shutil.copy2(p,O/'Original'/name)
    x,sr=sf.read(p,always_2d=True);mono=x.mean(axis=1)
    sf.write(O/'Analysis'/(p.stem+'-decoded.wav'),x,sr,subtype='FLOAT')
    high=signal.sosfiltfilt(signal.butter(3,500,fs=sr,btype='highpass',output='sos'),mono)
    hop=max(1,round(sr*.005));n=len(mono)//hop
    rms=np.sqrt(np.mean(high[:n*hop].reshape(n,hop)**2,axis=1)+1e-15)
    peaks,_=signal.find_peaks(rms,height=max(rms)*.07,prominence=max(rms)*.035,distance=round(.06/.005))
    events=[{'time':float((i+.5)*hop/sr),'high_rms_db':float(20*np.log10(rms[i]+1e-10))} for i in peaks]
    report[name]={'sample_rate':sr,'channels':x.shape[1],'duration':len(x)/sr,'peak':float(np.max(abs(x))),
                  'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'transients':events}
    ax=axes[row*2];step=max(1,len(x)//15000);ax.plot(np.arange(0,len(x),step)/sr,mono[::step],lw=.55,color='#274969')
    ax.plot((np.arange(n)+.5)*hop/sr,rms,color='#c65f36',lw=.8,label='>500Hz RMS')
    for event in events:ax.axvline(event['time'],alpha=.16,color='red');ax.text(event['time'],.86*max(abs(mono)),f"{event['time']:.2f}",fontsize=7,rotation=90)
    ax.set(title=name,xlim=(0,len(x)/sr),ylabel='Amplitude');ax.grid(alpha=.2)
    f,t,z=signal.stft(mono,fs=sr,nperseg=1024,noverlap=768)
    axes[row*2+1].pcolormesh(t,f,20*np.log10(abs(z)+1e-7),shading='auto',vmin=-85,vmax=-20,cmap='magma')
    axes[row*2+1].set(ylim=(40,16000),yscale='log',xlabel='Seconds',ylabel='Hz')
fig.savefig(O/'Analysis/source-waveforms.png',dpi=120)
(O/'Analysis/source.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
