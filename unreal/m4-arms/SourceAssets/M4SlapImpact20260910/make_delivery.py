from pathlib import Path
from bisect import bisect_right
import json,subprocess,re
from PIL import Image,ImageDraw,ImageFont
O=Path(__file__).resolve().parent;P=O.parents[1];out=O/'Delivery';out.mkdir(exist_ok=True)
ff=str(O.parent/'M4Infima/PreviewTools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe')
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20)
reports=[]
for label,name,length,origin in [('m4-slap-impact','M4_拍击提速50与枪身轻震_实际录音',14.2,2.8)]:
 run=P/'Saved/GunplayUpgrade'/label;files={int(p.stem.split('_')[1]):p for p in (run/'Frames').glob('Frame_*.png')};keys=sorted(files);fps=20;count=round(length*fps)
 log=(O/f'runtime-{label}.log').read_text(encoding='utf-8-sig',errors='replace')
 if origin:offset=json.loads((O/f'audio_validation_{label}.json').read_text())['first_audit_elapsed']
 else:offset=json.loads((O/'equip_audio_validation.json').read_text())['recording_start_game_time_from_stop']
 silent=out/(name+'_silent.mp4');proc=subprocess.Popen([ff,'-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','640x396','-r',str(fps),'-i','-','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(silent)],stdin=subprocess.PIPE)
 for i in range(count):
  p=files[keys[max(0,bisect_right(keys,i)-1)]];im=Image.new('RGB',(640,396),(17,23,30));im.paste(Image.open(p).convert('RGB').resize((640,360)),(0,0));draw=ImageDraw.Draw(im)
  draw.text((10,365),f'UE5 M4 | 实际游戏与混音 | {origin+i/fps:.2f}s',font=font,fill='white');proc.stdin.write(im.tobytes())
 proc.stdin.close();assert proc.wait()==0
 trim=origin-offset
 args=[ff,'-v','error','-y','-i',str(silent),'-i',str(run/'GunplayAudio.wav')]
 filt=f'atrim=start={trim},asetpts=PTS-STARTPTS' if trim>=0 else f'adelay={round(-trim*1000)}:all=1'
 dest=out/(name+'.mp4');subprocess.run(args+['-filter:a',filt,'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-t',str(length),'-movflags','+faststart',str(dest)],check=True)
 reports.append({'run':label,'output':str(dest),'fps':fps,'source_frames':len(files),'held_missing_frames':sum(i not in files for i in range(count)),'audio_origin_trim':trim,'note':'Same run rendered frames and actual mixer output. Missing screenshot indices hold previous frame; no per-event audio replacement or shifts.'})

(out/'preview_manifest.json').write_text(json.dumps(reports,indent=2,ensure_ascii=False),encoding='utf-8');print(json.dumps(reports,ensure_ascii=False))
