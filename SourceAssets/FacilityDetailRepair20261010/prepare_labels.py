"""Typeset near-view equipment plates at their physical aspect ratio."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'Authored/Textures';OUT.mkdir(parents=True,exist_ok=True)
im=Image.new('RGB',(2048,2048),(25,31,29));d=ImageDraw.Draw(im);rects={}
cards=[('mail','员工钥匙与信件','STAFF MAIL / KEY RETURN'),('mail1','01  值班室','DUTY OFFICE'),('mail2','02  员工宿舍','STAFF QUARTERS'),('mail3','03  设施管理','FACILITY SERVICES'),
 ('switch','三相隔离开关','QS-03   /   400 V AC   /   630 A'),('danger','危险：检修前断电','ISOLATE SUPPLY BEFORE SERVICE'),('powerid','配电设备  PW-03','IP54   /   50 Hz   /   INSPECT EACH SHIFT'),
 ('tools','检修工具 · 使用后归位','SERVICE TOOLS / RETURN AFTER USE'),('comms','值班通讯  03','DUTY LINE / PRESS TO CALL'),('panel','辅助电源配电','AUXILIARY SUPPLY / 230 V'),
 ('phase','L1       L2       L3','THREE PHASE / LIVE TERMINALS'),('off','0  OFF       I  ON','PADLOCK BEFORE MAINTENANCE')]
font='C:/Windows/Fonts/msyh.ttc'
for i,(key,cn,en) in enumerate(cards):
    x=16+(i%2)*1024;y=16+(i//2)*256;w,h=992,224;rects[key]=[x,y,x+w,y+h]
    d.rounded_rectangle((x,y,x+w-1,y+h-1),12,fill=(207,210,189),outline=(49,65,57),width=7)
    d.text((x+30,y+26),cn,font=ImageFont.truetype(font,54),fill=(31,44,38))
    d.text((x+32,y+127),en,font=ImageFont.truetype(font,27),fill=(38,52,44))
    d.line((x+32,y+109,x+w-32,y+109),fill=(106,116,94),width=2)
    d.text((x+32,y+175),'FT / '+str(i+1).zfill(3)+'     SERVICE COPY',font=ImageFont.truetype(font,20),fill=(66,78,65))
im.save(OUT/'T_FacilityDetail_Plates.png')
(ROOT/'atlas.json').write_text(json.dumps(dict(size=list(im.size),rects=rects),indent=2),encoding='utf8')
