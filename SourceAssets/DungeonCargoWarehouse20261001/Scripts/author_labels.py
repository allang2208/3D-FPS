import json,random
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored'
im=Image.new('RGB',(2048,2048),(178,177,157));d=ImageDraw.Draw(im)
font='C:/Windows/Fonts/msyh.ttc';rects={}
labels=[('Main','货运仓库','CARGO STORAGE / WH-04','停用仓储区 · 保持运输通道畅通'),
 ('Entry','货运转运间','TRANSFER GATE / INBOUND','唯一货运入口'),
 ('Exit','设施出口','ONWARD ACCESS / EXIT','沿黄线前进'),
 ('Dock','装卸平台','LOADING DOCK / 1.2 m','注意高差 · 请走楼梯'),
 ('RackW','西侧储存区','BAY W / PALLET STORAGE','禁止攀爬货架'),
 ('RackE','东侧储存区','BAY E / PALLET STORAGE','额定载荷 1000 kg / 层'),
 ('Hoist','起重设备停用','HOIST OUT OF SERVICE','检修锁定 · 禁止操作'),
 ('KeepClear','禁止堆放','KEEP CLEAR / TRANSPORT LANE','出入口及消防通道保持畅通')]
for i,(key,title,sub,small) in enumerate(labels):
    x=(i%2)*1024;y=(i//2)*400;rects[key]=(x+8,y+8,x+1016,y+392)
    d.rectangle(rects[key],fill=(194,194,173),outline=(44,51,43),width=10)
    d.rectangle((x+21,y+294,x+1003,y+377),fill=(186,149,45))
    for text,yy,size in [(title,102,72),(sub,218,34),(small,337,34)]:d.text((x+512,y+yy),text,font=ImageFont.truetype(font,size),fill=(33,41,36),anchor='mm')
rects['Stripe']=(12,1620,2036,1820);d.rectangle(rects['Stripe'],fill=(181,145,35))
for x in range(-200,2200,160):d.polygon([(x,1620),(x+80,1620),(x+280,1820),(x+200,1820)],fill=(28,31,28))
im.save(OUT/'T_CargoWarehouse_Labels_BaseColor.png')
(OUT/'atlas.json').write_text(json.dumps(dict(size=[2048,2048],rects=rects),indent=2),encoding='utf-8')
print('CARGO_WAREHOUSE_LABELS_WRITTEN')
