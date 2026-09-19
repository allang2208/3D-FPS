import wave,json,subprocess,re,sys
import numpy as np
from pathlib import Path
O=Path(__file__).resolve().parent;label=sys.argv[1] if len(sys.argv)>1 else 'm4-wrap-equip';run=O.parents[1]/'Saved/GunplayUpgrade'/label
with wave.open(str(run/'GunplayAudio.wav')) as w:
 rate=w.getframerate();pcm=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').reshape(-1,w.getnchannels()).mean(axis=1)/32768
ff=str(O.parent/'M4Infima/PreviewTools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe')
template=np.frombuffer(subprocess.check_output([ff,'-v','error','-i',str(O/'Audio/equip.wav'),'-ac','1','-ar',str(rate),'-f','f32le','-']),dtype='<f4').astype(float)
# Anchor at StopRecordingOutput, after startup stalls and mixer warm-up.
# First-frame time is not the beginning of the recorded mixer sample buffer.
samples=(run/'equip_samples.csv').read_text(encoding='utf-8-sig').splitlines()
offset=float(samples[-1].split(',')[0])-len(pcm)/rate
log=(O/f'runtime-{label}.log').read_text(encoding='utf-8-sig',errors='replace')
times=[float(re.search('GUNPLAY_ASSERT PASS '+name+r' t=([0-9.]+)',log)[1]) for name in ['inventory_equip_fixture','switch_uses_inventory_instance']];events=[]
for time in times:
 lo=round((time-offset-.2)*rate);hi=round((time-offset+.25)*rate)+len(template);seg=pcm[lo:hi];nfft=1<<(len(seg)+len(template)-1).bit_length()
 cross=np.fft.irfft(np.fft.rfft(seg,nfft)*np.conj(np.fft.rfft(template,nfft)),nfft)[:len(seg)-len(template)+1];en=np.r_[0,np.cumsum(seg**2)]
 corr=cross/np.sqrt(np.maximum(1e-20,(en[len(template):]-en[:-len(template)])*sum(template**2)));i=int(corr.argmax());events.append({'equip_at':time,'wave_start':(lo+i)/rate,'correlation':float(corr[i]),'audio_vs_game_seconds':(lo+i)/rate+offset-time})
report={'label':label,'recording_start_game_time_from_stop':offset,'events':events,'peak':float(abs(pcm).max()),'duration':len(pcm)/rate,'note':'Actual mixer recording; complete equip waveforms matched. Sample origin uses recording end because startup buffering makes the first-frame origin unreliable. Offset includes mixer-buffer latency; no individual sound is moved.'}
(O/'equip_audio_validation.json').write_text(json.dumps(report,indent=2));print(report);assert min(e['correlation'] for e in events)>.9

