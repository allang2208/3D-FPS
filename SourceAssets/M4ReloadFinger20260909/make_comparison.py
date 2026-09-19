from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
p=Path(__file__).resolve().parent
sheet=Image.new('RGB',(1400,610),(25,30,35));draw=ImageDraw.Draw(sheet)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',24)
for i,(label,name) in enumerate([('修改前：食指伸直','close_60_before.png'),('修改后：自然弯曲','close_60_after.png')]):
    with Image.open(p/name) as im:sheet.paste(im.convert('RGB').resize((700,560),Image.Resampling.LANCZOS),(i*700,50))
    draw.text((i*700+18,12),label,font=font,fill='white')
sheet.save(p/'finger_comparison.png')
