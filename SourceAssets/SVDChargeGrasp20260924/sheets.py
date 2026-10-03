from PIL import Image,ImageDraw
from pathlib import Path
import sys
O=Path(__file__).parent/'Review';label=sys.argv[1] if len(sys.argv)>1 else 'before'
files=sorted(O.glob(label+'_fp_*.png'));w=660;h=395;sheet=Image.new('RGB',(w*2,h*((len(files)+1)//2)),(22,26,32));draw=ImageDraw.Draw(sheet)
for i,file in enumerate(files):
 im=Image.open(file).convert('RGB');im.thumbnail((w,h-23));x=(i%2)*w;y=(i//2)*h
 sheet.paste(im,(x,y+23));draw.text((x+8,y+5),file.stem,fill='white')
sheet.save(O/(label+'_sheet.jpg'),quality=85)
