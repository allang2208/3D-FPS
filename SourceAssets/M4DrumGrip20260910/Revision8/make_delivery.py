from pathlib import Path
from datetime import datetime
import json,re,subprocess,wave
import numpy as np
import imageio_ffmpeg
from PIL import Image
O=Path(__file__).parent;root=O.parents[2];run='drum_flow_r8'
folder=root/'Saved/DrumGripAudit'/run;log=(O/f'runtime-{run}.log').read_text(encoding='utf-8-sig',errors='replace')
stamp=r'\[(\d{4}\.\d\d\.\d\d-\d\d\.\d\d\.\d\d:\d{3})\]'
parse=lambda s:datetime.strptime(s,'%Y.%m.%d-%H.%M.%S:%f')
origin=parse(re.search(stamp+r'.*PASS revised animation lengths match event clock',log)[1])
with wave.open(str(folder/'DrumAudio.wav')) as w:
 rate=w.getframerate();channels=w.getnchannels();pcm=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').reshape(-1,channels).astype(float)/32768
mono=pcm.mean(axis=1);duration=len(mono)/rate;ff=imageio_ffmpeg.get_ffmpeg_exe();events=[]
names={'MagOut':'mag_out','MagInsert':'mag_insert','MagSeat':'mag_seat','BoltRelease':'bolt_release'}
for m in re.finditer(stamp+r'.*DRUM_AUDIO: empty=(\d) index=(\d).*late=([\d.]+) sound=S_HK416_(\w+) played=(\d)',log):
 t=(parse(m[1])-origin).total_seconds();name=names[m[5]]
 source=root/'SourceAssets'/('M4SlapImpact20260910/Audio' if name=='bolt_release' else 'M4HK416Replica20260910/Audio')/(name+'.wav')
 template=np.frombuffer(subprocess.check_output([ff,'-v','error','-i',str(source),'-ac','1','-ar',str(rate),'-f','f32le','-']),dtype='<f4').astype(float)
 lo=max(0,round((t-.4)*rate));hi=min(len(mono),round((t+.5)*rate)+len(template));seg=mono[lo:hi]
 nfft=1<<(len(seg)+len(template)-1).bit_length();cross=np.fft.irfft(np.fft.rfft(seg,nfft)*np.conj(np.fft.rfft(template,nfft)),nfft)[:len(seg)-len(template)+1]
 energy=np.r_[0,np.cumsum(seg**2)];corr=cross/np.sqrt(np.maximum(1e-20,(energy[len(template):]-energy[:-len(template)])*sum(template**2)));i=int(np.argmax(corr))
 events.append({'name':name,'empty':bool(int(m[2])),'played':bool(int(m[6])),'correlation':float(corr[i]),'log_seconds':t,'wave_seconds':(lo+i)/rate,'lateness_seconds':float(m[4])})
report={'duration':duration,'rms':float(np.sqrt(np.mean(pcm**2))),'clipped_samples':int(np.sum(abs(pcm)>=.999)),'events':events,'origin':'log immediately before mixer recording starts; one common origin, no per-event audio shifts'}
(O/'audio_validation.json').write_text(json.dumps(report,indent=2))
assert len(events)==7 and all(e['played'] and e['correlation']>.8 for e in events),report
assert report['rms']>.001 and report['clipped_samples']==0,report
frames=[]
for m in re.finditer(stamp+r'.*DRUM_GRIP: FRAME clip=(\w+) index=(\d+) elapsed=([\d.]+)',log):
 p=folder/f'{m[2]}_{int(m[3]):03d}.png'
 if p.exists():frames.append(((parse(m[1])-origin).total_seconds(),p))
out=O/'Delivery';out.mkdir(exist_ok=True)
video=out/'M4_drum_reload_with_game_audio.mp4'
proc=subprocess.Popen([ff,'-y','-v','error','-f','rawvideo','-pixel_format','rgb24','-video_size','640x360','-framerate','30','-i','-','-i',str(folder/'DrumAudio.wav'),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(video)],stdin=subprocess.PIPE)
j=0;cache={}
for k in range(round(duration*30)):
 t=k/30
 while j+1<len(frames) and frames[j+1][0]<=t:j+=1
 p=frames[j][1]
 if p not in cache:cache[p]=Image.open(p).convert('RGB').resize((640,360)).tobytes()
 proc.stdin.write(cache[p])
proc.stdin.close();assert proc.wait()==0
(out/'manifest.json').write_text(json.dumps({'video':str(video),'actual_screenshots':len(frames),'video_fps':30,'duration':duration,'note':'Real game screenshots and same-process mixer audio on wall clock. Holds preceding frame between captures; first frame covers recording lead-in.'},indent=2))
print(json.dumps(report,indent=2));print(video)
