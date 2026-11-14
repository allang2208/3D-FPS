from pathlib import Path
from PIL import Image,ImageFont,ImageDraw
r=Path(__file__).resolve().parent
panels=[('参考图',r.parent/'FreightCartBay20261113/reference.png'),('UE 实景 · 维修推车固定机位',r/'delivery_REF_02_CartSurface.png')]
im=Image.new('RGB',(2096,1094),'#242423');d=ImageDraw.Draw(im);font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',25)
for col,(title,file) in enumerate(panels):
    x=16+1040*col;d.text((x,12),title,font=font,fill='#ebe7de')
    src=Image.open(file).convert('RGB');im.paste(src.resize((1024,1024),Image.Resampling.LANCZOS),(x,54))
im.save(r/'CartBay-UpperWall-Comparison.jpg',quality=95,subsampling=0)
