"""Original facility paperwork and safety print artwork; no scene preview."""
from pathlib import Path
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'Authored/Textures';OUT.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(101010)
W=2048
noise=rng.normal(0,1.8,(W,W,1))
rgb=np.clip(np.array([211,208,188])[None,None,:]+noise,0,255).astype('uint8')
image=Image.fromarray(rgb);draw=ImageDraw.Draw(image)
font=lambda size:ImageFont.truetype('C:/Windows/Fonts/consola.ttf',size)
# Four legible A4 forms use their own UV quadrant, not a repeated fake text texture.
for k,(title,sub) in enumerate((('TRANSFER REGISTER','CONCOURSE / SHIFT B'),('MAINTENANCE RECORD','SERVICE / MECHANICAL'),('EVACUATION ROSTER','CHECKPOINT / PERSONNEL'),('CLEANING LOG','LOWER GALLERY / ROUTE 02'))):
    x=(k%2)*1024;y=(k//2)*1024
    draw.rectangle((x+55,y+50,x+970,y+146),fill=(31,61,62))
    draw.text((x+82,y+68),'FACILITY  /  02',font=font(47),fill=(222,222,199))
    draw.text((x+73,y+180),title,font=font(43),fill=(36,42,39))
    draw.text((x+73,y+244),sub,font=font(26),fill=(57,66,62))
    draw.line((x+70,y+294,x+955,y+294),fill=(61,72,68),width=3)
    for j in range(11):
        yy=y+327+j*49
        draw.text((x+78,yy),f'{j+1:02d}  {82+k:02d}-{15+j:03d}',font=font(25),fill=(68,68,59))
        draw.line((x+330,yy+29,x+946,yy+29),fill=(103,111,100),width=2)
        for xx in (340,572,770):draw.line((x+xx,yy-4,x+xx,yy+45),fill=(115,120,109),width=1)
        if (j+k)%3!=1:draw.text((x+360,yy),('CLEARED','REASSIGNED','PENDING')[(j+k)%3],font=font(23),fill=(72,78,71))
    draw.text((x+77,y+911),f'REF. FT-02-{34+k}  /  CONTROLLED COPY',font=font(25),fill=(75,80,70))
    draw.rectangle((x+710,y+813,x+945,y+890),outline=(116,61,46),width=4)
    draw.text((x+731,y+831),'SHIFT B',font=font(33),fill=(116,61,46))
    # Faint handling creases in albedo, with modest contrast at gameplay scale.
    for xx in (x+490,x+499):draw.line((xx,y+10,xx+12,y+1015),fill=(196,192,173),width=2)
image.save(OUT/'T_Incident_Forms.png')
im=Image.new('RGB',(512,1024),(194,149,24));d=ImageDraw.Draw(im)
d.polygon([(256,64),(42,440),(470,440)],fill=(31,32,28))
d.polygon([(256,116),(83,417),(429,417)],fill=(213,170,30))
d.ellipse((232,179,273,220),fill=(26,30,26))
d.line([(250,231),(273,297),(233,340),(183,338)],fill=(26,30,26),width=22)
d.line([(268,279),(330,268)],fill=(26,30,26),width=18)
d.line([(273,297),(317,365),(369,372)],fill=(26,30,26),width=20)
for yy,word,size in ((482,'CAUTION',69),(619,'WET',87),(732,'FLOOR',79)):
    ft=font(size);bb=d.textbbox((0,0),word,font=ft);d.text(((512-bb[2])/2,yy),word,font=ft,fill=(25,28,25))
d.text((107,925),'FACILITY 02',font=font(34),fill=(44,47,33))
im.save(OUT/'T_Incident_Caution.png')
print('INCIDENT_PRINT_ARTWORK_WRITTEN')
