"""40% stable occupancy, with connected office strips and varied residential bays."""
from pathlib import Path
import sys,json,numpy as np
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parent));from design import *
out=R/'Textures';out.mkdir(exist_ok=True);report={}
for index,name in enumerate(FAMILIES):
 w=h=2048;im=Image.new('RGB',(w,h));d=ImageDraw.Draw(im);rng=np.random.default_rng(19024+index)
 office=name in OFFICES;unit=3 if office else 1;cols=24//unit
 # Deterministic spatial scores form lit departments/floors with intervening dark areas.
 scores=[]
 for row in range(32):
  for col in range(cols):
   score=.52*np.sin(row*.79+index)+.28*np.cos(col*1.71+row//4)+rng.uniform(-.65,.65)
   scores.append((score,row,col))
 count=round(len(scores)*.40);selected={(row,col) for _,row,col in sorted(scores,reverse=True)[:count]}
 for row,col in selected:
  x0=round(col*w/cols);x1=round((col+1)*w/cols);y=row*64
  color=np.array(PALETTE[name])*rng.uniform(.52,.78)
  if not office and rng.random()<.3:color=np.array((1.,.70,.40))*rng.uniform(.46,.68)
  tone=tuple(np.uint8(np.clip(color,0,1)*255))
  if office:
   # Three adjacent bays read as one broad strip, with a soft inner diffuser.
   d.rectangle((x0+10,y+23,x1-10,y+40),fill=tone)
   d.rectangle((x0+12,y+21,x1-12,y+22),fill=tuple(int(v*.45) for v in tone))
   d.rectangle((x0+12,y+41,x1-12,y+42),fill=tuple(int(v*.45) for v in tone))
  else:d.rectangle((x0+15,y+14,x1-15,y+43),fill=tone)
 # Keep the architectural family identity from V17 around these occupied bays.
 if name=='WarmBands':
  for row in range(3,32,4):d.rectangle((0,row*64+53,w-1,row*64+59),fill=(91,64,34))
 elif name=='PearlVertical':
  for col in (2,8,14,20):
   x=round(col*w/24);d.rectangle((x,64,x+7,h-65),fill=(55,74,92))
 elif name=='AmberTerrace':
  for row in range(4,32,6):d.rectangle((80,row*64+52,w-81,row*64+60),fill=(83,48,25))
 elif name=='BlueFrame':
  for x in (34,w-44):d.rectangle((x,0,x+9,h-1),fill=(10,32,89))
 elif name=='CopperArcade':
  for row in (7,15,23,31):d.rectangle((0,row*64+52,w-1,row*64+60),fill=(86,61,33))
 im.save(out/f'T_AP19_{name}_E.png')
 report[name]=dict(occupied_bays=count*unit,total_bays=768,ratio=count*unit/768,style='three_bay_horizontal_strips' if office else 'individual_windows',animated=False)
(R/'facade-source.json').write_text(json.dumps(report,indent=2),encoding='utf8');print('AP19_FACADES_AUTHORED')
