from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
out=Path(__file__).resolve().parents[1]/'RoomDetailsV5/Authored/toilet-sign.png'
im=Image.new('RGB',(640,256),(223,224,204));d=ImageDraw.Draw(im)
d.rectangle((7,7,632,248),outline=(31,51,44),width=6)
d.rectangle((13,13,626,49),fill=(31,51,44))
d.text((320,76),'员工卫生间',anchor='mt',font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',60),fill=(25,39,34))
d.text((320,161),'STAFF RESTROOM',anchor='mt',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',26),fill=(31,51,44))
d.text((320,202),'请保持清洁 · 使用后冲水',anchor='mt',font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20),fill=(46,63,51))
im.save(out)
