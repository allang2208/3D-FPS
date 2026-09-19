from PIL import Image,ImageDraw
from pathlib import Path
P=Path(__file__).parent/'Review'
for view in ('fp','grip'):
 out=Image.new('RGB',(1280,4*470),(25,28,32));draw=ImageDraw.Draw(out)
 for row,f in enumerate((0,12,20,60)):
  for col,rev in enumerate(('N','O')):
   out.paste(Image.open(P/f'{rev}_{view}_{f:03}.png'),(col*640,row*470+30))
   draw.text((col*640+12,row*470+8),f'{rev} | frame {f:03} | {view}',fill='white')
 out.save(P/f'{view}_comparison.jpg',quality=86)
pair=Image.new('RGB',(1280,470),(25,28,32));draw=ImageDraw.Draw(pair)
for col,rev in enumerate(('N','O')):
 pair.paste(Image.open(P/f'{rev}_grip_020.png'),(col*640,30))
 draw.text((col*640+12,8),'BEFORE - N' if rev=='N' else 'AFTER - O',fill='white')
pair.save(P/'contact_before_after.jpg',quality=85)
