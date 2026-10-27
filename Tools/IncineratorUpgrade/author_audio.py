"""Original deterministic seamless combustion loop; no external recordings."""
from pathlib import Path
import json
import wave
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/IncineratorUpgrade20261027'
OUT.mkdir(parents=True,exist_ok=True)
rate=48000;seconds=8;n=rate*seconds
rng=np.random.default_rng(271027)
frequency=np.fft.rfftfreq(n,1/rate)
t=np.arange(n)/rate
def band(lo,hi):
    power=(1-np.exp(-(frequency/max(lo,1))**4))*np.exp(-(frequency/hi)**4)
    spectrum=(rng.normal(size=frequency.size)+1j*rng.normal(size=frequency.size))*np.sqrt(power)
    spectrum[0]=0;spectrum[-1]=0
    signal=np.fft.irfft(spectrum,n=n)
    return signal/(np.std(signal)+1e-9)
# Pressurized air, low furnace roar and sparse rough combustion flutter.
# Every Fourier bin and modulation frequency completes an integer number of
# periods in eight seconds: the loop boundary has no artificial fade/dropout.
roar=band(45,420)
jet=band(280,3600)
texture=band(1400,7000)
envelope=.78+.12*np.sin(2*np.pi*.375*t)+.07*np.sin(2*np.pi*1.125*t+.7)
flutter=1+.09*np.sin(2*np.pi*19*t+.4)+.05*np.sin(2*np.pi*31.25*t)
signal=(.48*roar+.27*jet*flutter+.035*texture)*envelope
signal=np.tanh(signal*.9)
signal*=10**(-3/20)/np.max(np.abs(signal))
wav=OUT/'S_IncineratorCombustionLoop.wav'
with wave.open(str(wav),'wb') as output:
    output.setnchannels(1);output.setsampwidth(2);output.setframerate(rate)
    output.writeframes((signal*32767).astype('<i2').tobytes())
(OUT/'audio-source.json').write_text(json.dumps({
    'source':'Original procedural synthesis; no external samples',
    'file':str(wav),'duration_seconds':seconds,'sample_rate':rate,'channels':1,
    'peak_dbfs':-3,'rms_dbfs':float(20*np.log10(np.sqrt(np.mean(signal**2)))),
    'design':'Pressurized jet air + low combustion roar + flutter, seamless periodic source',
    'auditioned':False},indent=2),encoding='utf-8')
print(str(wav))
