from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
root=Path(__file__).resolve().parent
left=Image.open(root/'reference.png').convert('RGB')
right=Image.open(root/'station_bay_REF_02_CartSurface.png').convert('RGB')
width,height=right.size
out=Image.new('RGB',(width*2+52,height+90),'#1d201f');d=ImageDraw.Draw(out)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',25)
for x,text,im in [(18,'参考图',left),(width+34,'UE 实景　维修推车固定机位',right)]:
    d.text((x,13),text,font=font,fill='#ece7dc')
    out.paste(im.resize((width,height),Image.Resampling.LANCZOS),(x,56))
out.save(root/'CartBay-Reference-UE.jpg',quality=95,subsampling=0)
