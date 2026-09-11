"""Assemble actual game capture frames; never substitute source-model renders."""
from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
import sys
root=Path('D:/FPS3D/FPSGAME/Saved/TraversalRuntimeAudit')
run=root/(sys.argv[1] if len(sys.argv)>1 else 'ColdSteel_TraversalRuntimeAudit_v4')
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',15)
frames=[];durations=[]
course='--course' in sys.argv
cases=[(0,'0.8 米矮墙：翻越'),(1,'1.2 米中墙：翻越'),(2,'1.8 米高墙：攀爬'),(3,'1 米平台：撑上')] if course else [(0,'1 米薄墙：翻越'),(1,'1 米宽平台：撑上'),(2,'1.8 米高台：抓边攀爬')]
for case,label in cases:
 files=sorted(run.glob(f'case_{case}_frame_*.png'));assert files,run
 for f in files:
  im=Image.open(f).convert('RGB').resize((480,270))
  d=ImageDraw.Draw(im);d.rectangle((0,0,480,27),fill=(16,20,24));d.text((12,4),label+'  |  UE5 实机片段',font=font,fill='white')
  frames.append(im.quantize(colors=96,dither=Image.Dither.NONE));durations.append(67)
 if not course: durations[-1]=600
frames[0].save(run/'traversal_runtime.gif',save_all=True,append_images=frames[1:],duration=durations,loop=0,optimize=False)
print(run/'traversal_runtime.gif')
