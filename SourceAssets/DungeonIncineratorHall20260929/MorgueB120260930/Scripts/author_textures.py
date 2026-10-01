"""Original directional, mortuary and equipment identification artwork."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored/Textures';OUT.mkdir(parents=True,exist_ok=True)
im=Image.new('RGB',(2048,2048),(166,178,173));d=ImageDraw.Draw(im);rects={}
def text(x,y,t,size,width=920):
    while True:
        font=ImageFont.truetype('C:/Windows/Fonts/msyhbd.ttc',size)
        if d.textlength(t,font=font)<=width:break
        size-=1
    d.text((x,y),t,font=font,anchor='mm',fill=(24,39,37))
labels=[('stairs','B1  停尸房','下行 3.6 米 · 请走楼梯'),('foyer','遗体转运前室','MORTUARY / TRANSFER'),
        ('cold','遗体冷藏区','01—12  /  COLD STORAGE'),('wash','整理与清洁区','PREPARATION / WASH'),
        ('service','制冷设备间','设备停用 · 检修前隔离'),('ash','灰渣接收 · 检修区','设备停用 · 禁止投料'),
        ('transfer','后勤转运通道','通道封闭 / OUT OF SERVICE'),('machine','密闭干式接灰装置','先关闸门，再抽出接灰箱')]
for i,(key,title,sub) in enumerate(labels):
    x=(i%2)*1024+16;y=(i//2)*350+16;r=[x,y,x+992,y+320];rects[key]=r
    d.rectangle(r,fill=(186,196,179) if key!='stairs' else (193,156,53));d.rectangle([x+7,y+7,x+985,y+313],outline=(40,55,47),width=5)
    text(x+496,y+108,title,91);text(x+496,y+239,sub,49)
for slot in range(1,13):
    col=(slot-1)%6;row=(slot-1)//6;x=col*336+20;y=1430+row*240;r=[x,y,x+306,y+210];rects['slot%02d'%slot]=r
    d.rectangle(r,fill=(205,207,184));text(x+153,y+82,'%02d'%slot,100,280);text(x+153,y+165,'B1 / MORTUARY',23,280)
rects['steel']=[24,1950,180,2024];d.rectangle(rects['steel'],fill=(86,93,91))
im.save(OUT/'T_MorgueSigns_BaseColor.png');Image.new('RGB',(2048,2048),(255,175,0)).save(OUT/'T_MorgueSigns_ORM.png')
(ROOT/'Authored/sign_atlas.json').write_text(json.dumps({'rects':rects,'size':[2048,2048],'source':'Original typography, rendered Windows font artwork only'},ensure_ascii=False,indent=2),encoding='utf-8')
print('MORGUE_SIGN_ARTWORK_SAVED',flush=True)
