from pathlib import Path
from bisect import bisect_right
import subprocess,json
from PIL import Image,ImageDraw,ImageFont
O=Path(__file__).resolve().parent;P=O.parents[1];D=O/'Delivery';D.mkdir(exist_ok=True);ff=str(O.parent/'M4Infima/PreviewTools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe')
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',24)
labels=['m4-polish-av60-final','m4-contact-av60'];sources=[]
for label in labels:
 files={int(p.stem.split('_')[1]):p for p in (P/'Saved/GunplayUpgrade'/label/'Frames').glob('Frame_*.png')};sources.append((files,sorted(files)))
segments=[(72,115),(140,185)];silent=D/'comparison_silent.mp4';proc=subprocess.Popen([ff,'-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1280x404','-r','20','-i','-','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(silent)],stdin=subprocess.PIPE)
for lo,hi in segments:
 for i in range(lo,hi):
  im=Image.new('RGB',(1280,404),(15,20,25));draw=ImageDraw.Draw(im)
  for j,(files,keys) in enumerate(sources):
   key=keys[max(0,bisect_right(keys,i)-1)];im.paste(Image.open(files[key]).convert('RGB'),(640*j,44));draw.text((640*j+16,8),['上一版','本轮：退出避让 / 蓄势拍击'][j],font=font,fill='white')
  proc.stdin.write(im.tobytes())
proc.stdin.close();assert proc.wait()==0
offset=json.loads((O/'audio_validation_m4-contact-av60.json').read_text())['first_audit_elapsed'];filters=[]
for j,(lo,hi) in enumerate(segments):filters.append(f'[1:a]atrim=start={2.8+lo/20-offset}:end={2.8+hi/20-offset},asetpts=PTS-STARTPTS[a{j}]')
filters.append('[a0][a1]concat=n=2:v=0:a=1[a]')
out=D/'M4_插匣与拍击_前后对比.mp4';subprocess.run([ff,'-v','error','-y','-i',str(silent),'-i',str(P/'Saved/GunplayUpgrade/m4-contact-av60/GunplayAudio.wav'),'-filter_complex',';'.join(filters),'-map','0:v','-map','[a]','-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart',str(out)],check=True)
(D/'comparison_manifest.json').write_text(json.dumps({'before':labels[0],'after':labels[1],'fps':20,'segments':segments,'audio':'Current run mixer recording, trimmed with the same segment boundaries.','duration':sum(b-a for a,b in segments)/20},indent=2));print(out)
