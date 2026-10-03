from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
out=Path(__file__).parent/'Textures';out.mkdir(exist_ok=True)
image=Image.new('RGB',(2048,512),(231,235,226));d=ImageDraw.Draw(image)
cn='C:/Windows/Fonts/msyh.ttc';en='C:/Windows/Fonts/consola.ttf'
font=lambda size:ImageFont.truetype(cn,size)
mono=lambda size:ImageFont.truetype(en,size)
d.rectangle((0,0,2048,34),fill=(20,83,68))
d.rectangle((0,474,2048,512),fill=(20,83,68))
d.line((0,39,2048,39),fill=(177,156,103),width=4)
d.line((0,468,2048,468),fill=(177,156,103),width=4)
for center in (512,1536):
    d.ellipse((center-27,62,center+27,116),outline=(30,103,82),width=3)
    d.polygon([(center,70),(center-12,92),(center-9,105),(center+9,105),(center+12,92)],fill=(30,103,82))
    d.text((center,134),'清泉',font=font(110),fill=(22,76,61),anchor='mt')
    d.text((center,279),'天然矿泉水',font=font(35),fill=(36,96,79),anchor='mt')
    d.text((center,335),'NATURAL MINERAL WATER',font=mono(23),fill=(53,101,87),anchor='mt')
    d.text((center,399),'500 mL  ·  PURE & FRESH',font=mono(24),fill=(50,94,81),anchor='mt')
image.save(out/'T_MineralWater_Label.png')
