from pathlib import Path
import subprocess,imageio_ffmpeg,numpy as np,soundfile as sf
from PIL import Image,ImageDraw
from scipy.signal import find_peaks
p=Path('SourceAssets/PKMLowpoly20260922/UserRecording20260928');src=r'C:\Users\allan\Videos\NVIDIA\Delta Force\Delta Force 2026.09.28 - 22.35.40.01.mp4'
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-v','error','-ss','7.2','-i',src,'-t','7.4','-vf','fps=5,scale=480:-1',str(p/'detail_%03d.jpg')],check=True)
files=list(p.glob('detail_*.jpg'));out=Image.new('RGB',(1920,300*((len(files)+3)//4)));d=ImageDraw.Draw(out)
for i,path in enumerate(files):
 x=i%4*480;y=i//4*300;out.paste(Image.open(path),(x,y));d.text((x+5,y+270),f'{7.2+i*.2:.2f}s',fill='white')
out.save(p/'details.jpg')
x,s=sf.read(p/'recording.wav');step=240;e=np.array([np.sqrt(np.mean(x[i:i+step]**2)) for i in range(0,len(x)-step,step)]);peaks,_=find_peaks(e,distance=16,prominence=.008)
print([(round(i*.005,3),round(float(e[i]),3)) for i in peaks if i*.005>7.2]);print('peak',np.max(abs(x)))
