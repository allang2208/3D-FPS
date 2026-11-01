"""Original seamless magnetic hum and electrical rasp, modulated at runtime."""
from pathlib import Path
import hashlib,json
import numpy as np
import soundfile as sf

P=Path(__file__).resolve().parent
rate=48000; seconds=4; count=rate*seconds
t=np.arange(count)/rate; rng=np.random.default_rng(10302026)
# All oscillators and modulators complete integer cycles in the loop. Noise is
# shaped in the circular Fourier domain, so neither end needs a silent splice.
phase=2*np.pi*96*t+.18*np.sin(2*np.pi*4*t)
magnet=.50*np.sin(phase)+.23*np.sin(2*phase+.3)+.12*np.sin(4*phase+.7)
magnet+=.075*np.sin(2*np.pi*288*t+.6*np.sin(2*np.pi*1.25*t))
freq=np.fft.rfftfreq(count,1/rate)
noise=np.fft.rfft(rng.standard_normal(count))
band=(1-np.exp(-(freq/190)**4))*np.exp(-(freq/2100)**2)
electric=np.fft.irfft(noise*band,n=count);electric/=np.std(electric)
pulse=.12+.10*(.5+.5*np.sin(2*np.pi*12*t+.4*np.sin(2*np.pi*1.5*t)))**4
rasp=.055*np.sin(2*np.pi*768*t+1.1*np.sin(2*np.pi*24*t))
signal=np.tanh(magnet*(.90+.07*np.sin(2*np.pi*6*t))+pulse*electric+rasp)
signal-=signal.mean();signal*=.74/np.max(np.abs(signal))
file=P/'S_JiLei_ChargeElectromagnetic.wav';sf.write(file,signal,rate,subtype='PCM_16')
recipe={'revision':'JiLeiChargeAudioV1','file':file.name,'sample_rate':rate,'channels':1,
 'seconds':seconds,'loop':True,'source':'Original mathematical synthesis; no third-party samples',
 'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
 'runtime':'Charge controls volume 0.055 to 0.70, pitch 0.72 to 1.18, lowpass 520 to 3600 Hz; fade in 60 ms / out 80 ms',
 'gameplay_tested':False}
(P/'audio_manifest.json').write_text(json.dumps(recipe,indent=2),encoding='utf-8')
print('JI_LEI_ELECTROMAGNETIC_SOURCE_AUTHORED',file)
