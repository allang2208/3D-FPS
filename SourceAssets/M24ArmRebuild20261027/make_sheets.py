from pathlib import Path
from PIL import Image,ImageDraw
O=Path(__file__).resolve().parent
for role in ('fire','reload_empty','sprint_enter'):
 files=sorted((O/'ReviewFrames'/role).glob('*.png'),key=lambda p:int(p.stem))
 cols=3;w,h=480,292;sheet=Image.new('RGB',(cols*w,((len(files)+cols-1)//cols)*h),(25,29,34))
 for i,p in enumerate(files):
  img=Image.open(p).convert('RGB').resize((w,270));x=(i%cols)*w;y=(i//cols)*h;sheet.paste(img,(x,y));ImageDraw.Draw(sheet).text((x+10,y+272),role+' / frame '+p.stem,fill='white')
 sheet.save(O/(role+'_source_sheet.jpg'),quality=92)
