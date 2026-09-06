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
  if folder=='runtime-detail':
   w,h=im.size;im=im.crop((round(w*.32),round(h*.18),round(w*.62),round(h*.84)))
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
for clip,duration in [('Idle',1000),('Walk',1500),('Death',1400)]:
 paths=sorted((R/'runtime-detail'/clip).glob('*.png'))
 assert len(paths)=={'Idle':25,'Walk':37,'Death':35}[clip],(clip,len(paths))
 frames=[]
 for p in paths[:-1]:
  im=Image.open(p).convert('RGB');w,h=im.size
  # Death travels across the frame; keep a wider view for its full fall.
  box=(.23,.18,.74,.90) if clip=='Death' else (.32,.18,.62,.84)
  im=im.crop(tuple(round(v*(w if i%2==0 else h)) for i,v in enumerate(box)));im.thumbnail((960,540));frames.append(im)
 n=len(frames);delays=[round((i+1)*duration/n/10)*10-round(i*duration/n/10)*10 for i in range(n)]
 frames[0].save(R/(clip+'.gif'),save_all=True,append_images=frames[1:],duration=delays,loop=0,disposal=2,optimize=True)
 gif=Image.open(R/(clip+'.gif'));total=0
 for i in range(gif.n_frames):gif.seek(i);total+=gif.info['duration']
 assert total==duration
 report[clip]={'frames':gif.n_frames,'duration_ms':total,'inspection_lights':True}
 sheet=Image.new('RGB',(1440,1010),(25,25,25));draw=ImageDraw.Draw(sheet)
 for j in range(12):
  idx=round(j*(n-1)/11);im=frames[idx].copy();im.thumbnail((360,310));x=j%4*360;y=j//4*336;sheet.paste(im,(x,y));draw.text((x+8,y+313),f'{clip} {idx/24:.3f}s',fill='white')
 sheet.save(R/(clip+'-contact.jpg'),quality=90)
(R/'preview-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
