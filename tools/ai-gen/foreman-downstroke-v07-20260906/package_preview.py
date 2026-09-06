from pathlib import Path
from PIL import Image,ImageDraw
import json
R=Path(__file__).resolve().parent
report={}
for folder,name in [('runtime-lit','Attack-review'),('runtime','Attack'),('runtime-detail','Attack-detail')]:
 paths=sorted((R/folder/'Attack').glob('*.png'))
 if not paths:continue
 assert len(paths)==37,(folder,len(paths))
 frames=[]
 for p in paths[:-1]:
  im=Image.open(p).convert('RGB')
  if folder=='runtime-detail':im=im.crop((640,280,1240,920))
  im.thumbnail((960,540));frames.append(im)
 delays=[round((i+1)*150/36)*10-round(i*150/36)*10 for i in range(36)]
 frames[0].save(R/(name+'.gif'),save_all=True,append_images=frames[1:],duration=delays,loop=0,disposal=2,optimize=True)
 gif=Image.open(R/(name+'.gif'));total=0
 for i in range(gif.n_frames):gif.seek(i);total+=gif.info['duration']
 assert total==1500
 report[name]={'frames':gif.n_frames,'duration_ms':total,'inspection_lights':folder in ['runtime-lit','runtime-detail']}
 for page in range(3):
  sheet=Image.new('RGB',(1440,1010),(25,25,25));d=ImageDraw.Draw(sheet)
  for j in range(12):
   idx=page*12+j;im=frames[idx].copy();im.thumbnail((360,310));x=j%4*360;y=j//4*336;sheet.paste(im,(x,y));d.text((x+8,y+313),f'{idx:02d}  {idx/24:.3f}s',fill='white')
  sheet.save(R/f'{name}-frames-{page}.jpg',quality=90)
(R/'preview-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
