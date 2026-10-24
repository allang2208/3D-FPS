"""New architectural light masks, drawn from facade grammar rather than white noise."""
from pathlib import Path
import sys,json,numpy as np
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parent));from design import *
out=R/'Textures';out.mkdir(exist_ok=True);report={}
for index,name in enumerate(FAMILIES):
 w=h=2048;im=Image.new('RGB',(w,h));d=ImageDraw.Draw(im);rng=np.random.default_rng(1700+index)
 color=np.array(PALETTE[name]);lit=0
 # Coherent occupied office bays, large dark floors and mechanical belts.
 for row in range(32):
  for col in range(24):
   bay=col//3;zone=row//4;seed=(bay*17+zone*23+index*11)%19
   active=seed<5 and row%8 not in (0,7) and rng.random()<.48
   if name=='QuietGlass':active=active and col%3==0
   if not active:continue
   x0=round(col*w/24);x1=round((col+1)*w/24);y=row*64
   tone=tuple(np.uint8(np.clip(color*rng.uniform(.11,.24),0,1)*255))
   d.rectangle((x0+15,y+14,x1-15,y+43),fill=tone);lit+=1
 # Broad architectural highlights: much larger than individual windows.
 if name=='WarmBands':
  for row in range(3,32,4):d.rectangle((0,row*64+51,w-1,row*64+60),fill=(108,66,26))
 elif name=='PearlVertical':
  for col in (2,8,14,20):
   x=round(col*w/24);d.rectangle((x,64,x+8,h-65),fill=(61,78,96))
 elif name=='AmberTerrace':
  for row in range(4,32,6):d.rectangle((80,row*64+50,w-81,row*64+61),fill=(92,46,17))
 elif name=='BlueFrame':
  for x in (34,w-44):d.rectangle((x,0,x+10,h-1),fill=(8,31,101))
 elif name=='CopperArcade':
  for row in (7,15,23,31):d.rectangle((0,row*64+50,w-1,row*64+61),fill=(93,57,23))
 im.save(out/f'T_AP17_{name}_E.png');report[name]=dict(lit_windows=lit,total_windows=768,animated=False)
(R/'facade-source.json').write_text(json.dumps(report,indent=2))
