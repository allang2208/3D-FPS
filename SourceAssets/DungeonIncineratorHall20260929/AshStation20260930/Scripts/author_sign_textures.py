"""Original Chinese industrial signage. Pixels are mapped onto the sole plate face."""
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored/Textures';OUT.mkdir(exist_ok=True)
W=2048;H=2048
im=Image.new('RGB',(W,H),(175,178,165));d=ImageDraw.Draw(im);rects={}
def f(size,bold=False):return ImageFont.truetype('C:/Windows/Fonts/'+('msyhbd.ttc' if bold else 'msyh.ttc'),size)
def panel(key,r,color=(183,181,159)):
    rects[key]=r;d.rectangle(r,fill=color);d.rectangle((r[0]+9,r[1]+9,r[2]-9,r[3]-9),outline=(34,41,38),width=8);return r
def text(r,y,t,size,fill=(29,36,32),bold=False):d.text(((r[0]+r[2])/2,y),t,font=f(size,bold),anchor='mm',fill=fill)
r=panel('main',(24,24,2024,825));text(r,167,'灰渣接收 · 检修区',138,bold=True);text(r,335,'下行 1.2 米   请走楼梯',90)
d.rectangle((r[0]+12,453,r[2]-12,620),fill=(180,131,39));text(r,535,'设备停用 · 检修前隔离',95,bold=True)
text(r,720,'AS-01   /   ASH RECEIVING BAY',62)
r=panel('machine',(24,860,2024,1405));text(r,990,'密闭干式接灰装置',124,bold=True);text(r,1166,'先关闸门，再抽出接灰箱',90)
text(r,1322,'AS-01  /  已停用 · 禁止投料',65)
r=panel('caution',(24,1440,1300,2024),(189,144,40));text(r,1580,'注意高差',132,bold=True);text(r,1747,'保持检修通道畅通',71);text(r,1900,'请走楼梯',94,bold=True)
r=panel('gate',(1330,1440,2024,1750));text(r,1530,'隔离闸门',70,bold=True);text(r,1668,'关闭  ◀  OPEN',48)
r=panel('bin',(1330,1780,2024,2024));text(r,1855,'接灰箱',81,bold=True);text(r,1960,'冷却后转运',48)
im.save(OUT/'T_AshStation_Signage_BaseColor.png')
orm=Image.new('RGB',(W,H),(255,160,0));orm.save(OUT/'T_AshStation_Signage_ORM.png')
(ROOT/'Authored/sign_atlas.json').write_text(json.dumps({'size':[W,H],'rects':rects,'source':'Original Chinese typeset signage; Microsoft YaHei rendered as artwork, font not redistributed'},ensure_ascii=False,indent=2),encoding='utf-8')
print('ASH_STATION_SIGNS_AUTHORED',flush=True)
