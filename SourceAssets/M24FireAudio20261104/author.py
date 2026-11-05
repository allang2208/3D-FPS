"""Master the supplied M24 single shot and derive a matched-level suppressor."""
from pathlib import Path
import hashlib
import json
import numpy as np
from scipy import signal
import soundfile as sf
import imageio_ffmpeg, subprocess

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parents[2]/'资产/音效/M24.mp3'
FS=48000
def decode():
    cmd=[imageio_ffmpeg.get_ffmpeg_exe(),'-nostdin','-v','error','-i',str(SOURCE),
         '-map','0:a:0','-ar',str(FS),'-ac','2','-f','f32le','-acodec','pcm_f32le','pipe:1']
    raw=subprocess.run(cmd,stdout=subprocess.PIPE,check=True).stdout
    return np.frombuffer(raw,dtype='<f4').reshape(-1,2).astype(np.float64)
def filt(x,b,a):
    return signal.lfilter(b,a,x,axis=0)
def bell(x,hz,q,dB):
    omega=2*np.pi*hz/FS; alpha=np.sin(omega)/(2*q); amp=10**(dB/40); c=-2*np.cos(omega)
    return filt(x,[1+alpha*amp,c,1-alpha*amp],[1+alpha/amp,c,1-alpha/amp])
def band(x,cut,btype):
    sos=signal.butter(2,cut,fs=FS,btype=btype,output='sos')
    return signal.sosfilt(sos,x,axis=0)
def kenergy(x):
    # BS.1770 K weighting at 48 kHz, summed L/R exposure. No LUFS gating.
    y=filt(x,[1.53512485958697,-2.69169618940638,1.19839281085285],
             [1.,-1.69065929318241,.73248077421585])
    y=filt(y,[1.,-2.,1.],[1.,-1.99004745483398,.99007225036621])
    return np.sum(y*y)/FS
def truepeak(x):
    return float(np.max(abs(signal.resample_poly(x,4,1,axis=0))))
def soft_peak(x,threshold,span):
    # Stereo-linked knee to round excessive peaks while retaining the stereo image.
    peak=np.max(abs(x),axis=1,keepdims=True)
    excess=np.maximum(peak-threshold,0.)
    limited=np.minimum(peak,threshold)+span*np.tanh(excess/span)
    return x*np.divide(limited,peak,out=np.ones_like(peak),where=peak>0)
def design(x):
    t=np.arange(len(x))[:,None]/FS
    body=band(x,38,'highpass')
    body=bell(body,87,.85,-2.3)
    body=bell(body,270,.86,3.6)
    body=bell(body,655,1.20,-2.3)
    # Smoothly tuck the broad muzzle crack under the pressure pulse. Leave a
    # narrow, dry edge from the original shot for definition at short range.
    body-=.71*band(body,2050,'highpass')
    body=bell(body,1280,1.18,2.1)
    mid=body.mean(axis=1,keepdims=True)
    body=mid+(body-mid)*(.70+.14*np.exp(-t/.09))
    tail=.27+.73*np.exp(-np.maximum(t-.072,0)/.145)
    edge=band(x,[1850,4900],'bandpass')*(.18*np.exp(-t/.043))
    result=body*tail+edge
    result*=np.sqrt(kenergy(x)/kenergy(result))
    # Settle the crest before the final loudness match, without turning down
    # the ordinary shot to accommodate a few narrow filtered peaks.
    peak=np.max(abs(x))
    result=soft_peak(result,.78*peak,.19*peak)
    return result*np.sqrt(kenergy(x)/kenergy(result))
raw=decode()
# This recording's initial 31 ms are codec lead-in. Keep the quiet precursor
# immediately before the first sharp rise, and leave a faded end to its real tail.
first=round(FS*.031);end=round(FS*.858)
normal=raw[first:end].copy()
normal[:48]*=np.linspace(0,1,48)[:,None]
normal[-384:]*=np.linspace(1,0,384)[:,None]
suppressed=design(normal)
gain=10**(-1.15/20)/max(truepeak(normal),truepeak(suppressed))
receipt={'source':str(SOURCE),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
         'decoded_frames':len(raw),'trim_frames':[first,end],'sample_rate':FS,'channels':2,
         'matched_level':'per-shot ungated K-weighted stereo energy','shared_gain_db':20*np.log10(gain),'masters':{}}
for name,x in [('S_M24_Fire',normal),('S_M24_Suppressed',suppressed)]:
    path=HERE/(name+'.wav')
    x=x*gain
    sf.write(path,x,FS,subtype='PCM_16')
    receipt['masters'][name]={'wav':path.name,'frames':len(x),'dBTP_4x':20*np.log10(truepeak(x)),
                              'K_exposure_dB':10*np.log10(kenergy(x)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
(HERE/'mastering.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(receipt['masters'],indent=2))
