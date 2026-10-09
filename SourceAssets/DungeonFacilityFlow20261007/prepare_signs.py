from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'Authored';OUT.mkdir(exist_ok=True)
names={'freight':'货运车站','medical':'医疗区','treatment':'焚化通风区','staff_living':'生活区','ecology':'生态区','power':'发电区'}
image=Image.new('RGB',(4096,2048),(28,39,35));draw=ImageDraw.Draw(image)
font=ImageFont.truetype('C:/Windows/Fonts/simhei.ttf',53);small=ImageFont.truetype('C:/Windows/Fonts/simhei.ttf',31)
rows=[]
for a in names:
    for b in names:
        if a==b:continue
        i=len(rows);x=i%4*1024;y=i//4*256
        draw.rectangle((x+7,y+7,x+1016,y+248),outline=(168,164,125),width=3)
        draw.rectangle((x+25,y+32,x+34,y+220),fill=(201,179,111))
        draw.text((x+64,y+44),'路线顺序 / ROUTE SEQUENCE',font=small,fill=(189,189,164))
        draw.text((x+64,y+124),names[a]+'  >  '+names[b],font=font,fill=(225,226,205))
        rows.append(dict(key=a+'__'+b,rect=[x,y,x+1024,y+256]))
image.save(OUT/'T_FacilityRoutePairs.png')
(ROOT/'pair-signs.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
