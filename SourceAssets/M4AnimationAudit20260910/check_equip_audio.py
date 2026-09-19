import wave,json,subprocess
import numpy as np
from pathlib import Path
O=Path(__file__).resolve().parent;run=O.parents[1]/'Saved/GunplayUpgrade/m4-audit-equip'
with wave.open(str(run/'GunplayAudio.wav')) as w:
 rate=w.getframerate();pcm=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').reshape(-1,w.getnchannels()).mean(axis=1)/32768
ff=str(O.parent/'M4Infima/PreviewTools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe')
template=np.frombuffer(subprocess.check_output([ff,'-v','error','-i',str(O/'Audio/equip.wav'),'-ac','1','-ar',str(rate),'-f','f32le','-']),dtype='<f4').astype(float)
offset=float((run/'equip_samples.csv').read_text(encoding='utf-8-sig').splitlines()[0].split(',')[0]);events=[]
for time in [1.6,3.5]:
 lo=round((time-offset-.2)*rate);hi=round((time-offset+.25)*rate)+len(template);seg=pcm[lo:hi];nfft=1<<(len(seg)+len(template)-1).bit_length()
 cross=np.fft.irfft(np.fft.rfft(seg,nfft)*np.conj(np.fft.rfft(template,nfft)),nfft)[:len(seg)-len(template)+1];en=np.r_[0,np.cumsum(seg**2)]
 corr=cross/np.sqrt(np.maximum(1e-20,(en[len(template):]-en[:-len(template)])*sum(template**2)));i=int(corr.argmax());events.append({'equip_at':time,'wave_start':(lo+i)/rate,'correlation':float(corr[i])})
report={'events':events,'peak':float(abs(pcm).max()),'duration':len(pcm)/rate,'note':'Actual mixer recording correlated with contact-aligned HK416 equip WAV. Interrupted equips are checked by runtime voice/queue assertions.'}
(O/'equip_audio_validation.json').write_text(json.dumps(report,indent=2));print(report);assert min(e['correlation'] for e in events)>.9

