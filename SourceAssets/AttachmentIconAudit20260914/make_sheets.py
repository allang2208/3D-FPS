from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import math,sys
P=Path(__file__).resolve().parent;O=P/'Icons';files=sorted(O.glob('*.png'))
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
for start in range(0,len(files),12):
 batch=files[start:start+12];sheet=Image.new('RGB',(1600,math.ceil(len(batch)/4)*350),(32,38,44));d=ImageDraw.Draw(sheet)
 for j,path in enumerate(batch):
  im=Image.open(path).convert('RGBA');im.thumbnail((350,270));x=j%4*400;y=j//4*350;sheet.paste(im,(x+(400-im.width)//2,y+5),im)
  label=path.stem.replace('ue_dan_wesson715_','DW715 / ').replace('ue_m1911_','M1911 / ').replace('ue_qbz191_','QBZ / ').replace('ue_akm_','AKM / ')
  d.text((x+9,y+280),label,font=font,fill=(230,235,240))
  tiny=Image.open(path).convert('RGBA');tiny.thumbnail((64,64));sheet.paste(tiny,(x+325,y+278),tiny)
 sheet.save(P/f'after_icons_{start//12+1}.png')
print('REVIEW_SHEETS',len(files),math.ceil(len(files)/12))
