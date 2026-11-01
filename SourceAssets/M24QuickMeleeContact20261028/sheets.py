from pathlib import Path
from PIL import Image,ImageDraw
O=Path(__file__).resolve().parent
for folder in ('Before','After'):
 if not (O/folder).exists():continue
 for view in ('fps','right'):
  frames=(.1,.15,.2,.25,.325,.46);out=Image.new('RGB',(1350,640),(25,28,32));d=ImageDraw.Draw(out)
  for i,t in enumerate(frames):
   p=O/folder/(f'{t:.3f}_{view}.png')
   if not p.exists():continue
   im=Image.open(p).resize((450,300));x=i%3*450;y=i//3*320;out.paste(im,(x,y+20));d.text((x+8,y+4),f'{folder}  {t:.3f}s',fill='white')
  out.save(O/(folder+'_'+view+'.jpg'),quality=92)
