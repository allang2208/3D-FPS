from pathlib import Path
import subprocess,imageio_ffmpeg
from PIL import Image,ImageDraw
p=Path('SourceAssets/PKMLowpoly20260922/RightReload51');src=r'C:\Users\allan\Videos\NVIDIA\Delta Force\Delta Force 2026.09.28 - 22.35.40.01.mp4'
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-v','error','-ss','12.35','-i',src,'-t','2.10','-vf','fps=10,crop=1700:1000:650:440,scale=425:250',str(p/'ref_%03d.jpg')],check=True)
files=sorted(p.glob('ref_*.jpg'));sheet=Image.new('RGB',(1700,280*((len(files)+3)//4)));d=ImageDraw.Draw(sheet)
for i,f in enumerate(files):
 x=i%4*425;y=i//4*280;sheet.paste(Image.open(f),(x,y));d.text((x+5,y+254),f'{12.35+i*.1:.2f}s',fill='white')
sheet.save(p/'reference_right_hand.jpg',quality=85)
