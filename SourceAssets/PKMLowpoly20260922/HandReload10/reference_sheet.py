from pathlib import Path
from PIL import Image,ImageDraw
O=Path(__file__).parent;files=sorted((O/'ReferenceFrames').glob('*.png'))
for group in range(2):
 chosen=files[group*16:(group+1)*16];sheet=Image.new('RGB',(1920,1200),(20,24,30));draw=ImageDraw.Draw(sheet)
 for i,file in enumerate(chosen):
  im=Image.open(file).convert('RGB');im.thumbnail((480,270));x=(i%4)*480;y=(i//4)*300
  sheet.paste(im,(x,y));draw.text((x+8,y+272),file.stem+' s',fill='white')
 sheet.save(O/f'reference_detail_{group+1}.jpg',quality=87)
