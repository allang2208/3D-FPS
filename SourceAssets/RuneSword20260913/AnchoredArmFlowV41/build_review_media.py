"""Compose proof sheets and a normal-speed clip from actual UE capture frames."""
from pathlib import Path
from PIL import Image,ImageDraw
import subprocess,json
import imageio_ffmpeg
P=Path(__file__).parent;A=P/'UEAfterV41';B=P/'UEBeforeV40'
files=[A/f'frame_{i*4:03d}.png' for i in range(88)]
if not all(f.exists() for f in files):raise RuntimeError('The full UE capture sequence is not finished')
for group,start in enumerate(range(0,len(files),24),1):
    subset=files[start:start+24];sheet=Image.new('RGB',(1280,210*((len(subset)+3)//4)),(27,30,36));draw=ImageDraw.Draw(sheet)
    for j,f in enumerate(subset):
        x=(j%4)*320;y=(j//4)*210
        sheet.paste(Image.open(f).convert('RGB').resize((320,180)),(x,y+30))
        draw.text((x+10,y+9),f'V41 | {(start+j)/30:.3f}s',fill='white')
    sheet.save(P/f'ue_frames_{group:02d}.jpg',quality=95)
sheet=Image.new('RGB',(1600,490),(27,30,36));draw=ImageDraw.Draw(sheet)
for j,(folder,label) in enumerate([(B,'V40 - exposed upper-arm cut'),(A,'V41 - upper arm connects below camera')]):
    sheet.paste(Image.open(folder/'frame_036.png').convert('RGB').resize((800,450)),(j*800,40));draw.text((j*800+15,15),label+' | 0.300s',fill='white')
sheet.save(P/'V40_V41_connection_comparison.jpg',quality=97)
frames=P/'PreviewFrames';frames.mkdir(exist_ok=True)
for i,f in enumerate(files):Image.open(f).convert('RGB').save(frames/f'{i:04d}.png')
ff=imageio_ffmpeg.get_ffmpeg_exe()
subprocess.run([ff,'-hide_banner','-loglevel','error','-y','-framerate','30','-i',str(frames/'%04d.png'),
    '-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(P/'V41_UE_preview.mp4')],check=True)
subprocess.run([ff,'-hide_banner','-loglevel','error','-y','-i',str(P/'V41_UE_preview.mp4'),
    '-vf','fps=30,scale=640:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse',
    '-loop','0',str(P/'V41_UE_preview.gif')],check=True)
print('UE_MEDIA_COMPLETE',len(files),'frames')
