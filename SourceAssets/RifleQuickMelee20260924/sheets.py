from pathlib import Path
from PIL import Image,ImageDraw
O=Path(__file__).parent/'Review'
for rev in ['before','after']:
 for weapon in ['SVD','PKM']:
  files=[O/f'{rev}_{weapon}_{view}_{t:03}.png' for view in ['fp','oblique'] for t in [75,167,300,520,720]]
  if not all(p.exists() for p in files):continue
  result=Image.new('RGB',(1500,440),(30,30,30));draw=ImageDraw.Draw(result)
  for i,p in enumerate(files):
   im=Image.open(p).convert('RGB');im.thumbnail((300,200));x=(i%5)*300;y=(i//5)*220
   result.paste(im,(x,y+20));draw.text((x+5,y+3),p.stem,fill='white')
  result.save(O/f'{rev}_{weapon}_sheet.jpg',quality=84)
