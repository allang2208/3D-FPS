from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
O=Path(__file__).resolve().parent/'Comparison';font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',24)
for view in ('side','wrist','palm','fps'):
    out=Image.new('RGB',(1600,592),(24,28,34));draw=ImageDraw.Draw(out)
    for col,(label,title) in enumerate((('before','修改前'),('after','本次修订'))):
        out.paste(Image.open(O/(label+'_'+view+'.png')).convert('RGB'),(col*800,52));draw.text((col*800+18,10),title+' · 离线姿态',font=font,fill=(235,239,243))
    out.save(O/(view+'_comparison.jpg'),quality=90)
print('IDLE_COMPARISONS_READY')
