from pathlib import Path
import subprocess,imageio_ffmpeg
from PIL import Image,ImageDraw
p=Path('SourceAssets/PKMLowpoly20260922/UserRecording20260928'); f=imageio_ffmpeg.get_ffmpeg_exe(); src=r'C:\Users\allan\Videos\NVIDIA\Delta Force\Delta Force 2026.09.28 - 22.35.40.01.mp4'
r=subprocess.run([f,'-hide_banner','-i',src],capture_output=True,text=True);print(r.stderr)
subprocess.run([f,'-y','-v','error','-i',src,'-vf','fps=2,scale=480:-1',str(p/'frame_%03d.jpg')],check=True)
subprocess.run([f,'-y','-v','error','-i',src,'-vn','-map','0:a:0','-ar','48000','-ac','2','-c:a','pcm_s16le',str(p/'recording.wav')],check=True)
files=list(p.glob('frame_*.jpg'));out=Image.new('RGB',(1920,300*((len(files)+3)//4))); d=ImageDraw.Draw(out)
for i,path in enumerate(files):
 im=Image.open(path); x=i%4*480;y=i//4*300;out.paste(im,(x,y));d.text((x+5,y+270),f'{i*.5:.2f}s',fill='white')
out.save(p/'timeline.jpg')
