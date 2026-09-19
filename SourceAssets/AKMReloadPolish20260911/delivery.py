import re,json,subprocess,wave
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import imageio_ffmpeg,numpy as np
O=Path(__file__).parent;P=O.parents[1];D=O/'Delivery';D.mkdir(exist_ok=True);report={};ff=imageio_ffmpeg.get_ffmpeg_exe()
for run in ['akm-polish-angled-v1','akm-polish-side-v2']:
 text=(O/f'runtime-{run}.log').read_text(encoding='utf-8');start=float(re.search(r'AKM_POLISH_AUDIO_START time=([\d.]+)',text)[1]);S=P/'Saved/ForegripAudit'/run
 rows=[(n,float(t),float(src)) for n,t,src in re.findall(r'AKM_POLISH_FRAME name=(\w+) time=([\d.]+) source=([\d.]+)',text)]
 wav=S/'AKMReloadAudio.wav'
 with wave.open(str(wav)) as w:rate=w.getframerate();channels=w.getnchannels();samples=np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).reshape(-1,channels).astype(float)/32768
 for clip,returned in [('drum_normal','returned_10'),('drum_empty','returned_12')]:
  seq=[r for r in rows if r[0].startswith(clip+'_') or r[0]==returned];seq.sort(key=lambda r:r[1]);assert all((S/(r[0]+'.png')).exists() for r in seq)
  span=seq[-1][1]-seq[0][1]+.35;lines=[]
  for i,(name,t,src) in enumerate(seq):
   dur=seq[i+1][1]-t if i+1<len(seq) else .35;lines.extend(["file '"+(S/(name+'.png')).as_posix()+"'",f'duration {dur:.6f}'])
  lines.append(lines[-2]);lst=D/(run+'_'+clip+'.txt');lst.write_text('\n'.join(lines))
  out=D/(('side' if 'side' in run else 'first_person')+'_'+clip+'.mp4')
  subprocess.run([ff,'-y','-v','error','-safe','0','-f','concat','-i',str(lst),'-ss',str(seq[0][1]-start),'-i',str(wav),'-t',str(span),'-vf','scale=800:560','-r','30','-c:v','libx264','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-movflags','+faststart',str(out)],check=True)
  seg=samples[max(0,int((seq[0][1]-start)*rate)):int((seq[-1][1]-start)*rate)]
  report[out.name]={'captured_frames':len(seq),'max_frame_gap_s':max(b[1]-a[1] for a,b in zip(seq,seq[1:])),'duration_s':span,'audio_rms':float(np.sqrt(np.mean(seg**2))),'audio_peak':float(np.max(abs(seg)))}
  assert report[out.name]['audio_rms']>.00001
  if 'side' in run and clip=='drum_normal':
   sheet=Image.new('RGB',(1200,840),'#181b21');draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',18)
   for i,f in enumerate([40,56,64,76,86,100]):
    n,t,src=min(seq,key=lambda r:abs(r[2]*120-f));x=i%3*400;y=i//3*420;sheet.paste(Image.open(S/(n+'.png')).convert('RGB').resize((400,280)),(x,y+35));draw.text((x+10,y+7),f'Source frame {src*120:.1f}',font=font,fill='white')
   sheet.save(D/'extraction-sequence.jpg',quality=92)
(D/'capture-report.json').write_text(json.dumps(report,indent=2));print('AKM_POLISH_DELIVERY_PASS')
