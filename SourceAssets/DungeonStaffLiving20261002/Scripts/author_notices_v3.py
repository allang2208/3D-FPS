"""Author real staff notices as typography, with no render or game run."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'RefinementV3/Authored';OUT.mkdir(parents=True,exist_ok=True)
FONT='C:/Windows/Fonts/msyh.ttc'
im=Image.new('RGB',(4096,2048),(190,185,166));d=ImageDraw.Draw(im)
def font(n):return ImageFont.truetype(FONT,n)
pages={}
def paper(index,title,subtitle):
    x=index*1024;y=8
    d.rectangle((x+12,y,x+1012,1530),fill=(224,218,196),outline=(98,104,88),width=5)
    d.rectangle((x+36,34,x+988,161),fill=(40,65,58))
    d.text((x+64,58),title,font=font(58),fill=(239,234,211))
    d.text((x+64,179),subtitle,font=font(28),fill=(69,81,71))
    d.line((x+62,233,x+962,233),fill=(124,128,106),width=3)
    pages[str(index)]=[x+12,y,x+1012,1530]
    return x,267
def line(x,y,text,size=34,color=(43,54,46)):
    d.text((x+65,y),text,font=font(size),fill=color)
    return y+size+22
def section(x,y,title,lines):
    d.rectangle((x+60,y,x+964,y+58),fill=(188,195,174))
    d.text((x+75,y+5),title,font=font(35),fill=(35,63,50));y+=78
    for text in lines:y=line(x,y,text)
    return y+24

x,y=paper(0,'本周值班安排','生活区管理处 / 第 40 周 / 周一至周日')
d.text((x+64,y),'交班前巡查：门窗、照明、供水、通道',font=font(32),fill=(47,65,52));y+=78
columns=[62,208,453,694,962]
headers=['日期','早班 06–14','中班 14–22','夜班 22–06']
rows=[['周一','陈林 / 101','李明 / 103','周诚 / 105'],['周二','赵海 / 102','王宁 / 104','何涛 / 106'],
      ['周三','李明 / 103','周诚 / 105','陈林 / 101'],['周四','王宁 / 104','何涛 / 106','赵海 / 102'],
      ['周五','周诚 / 105','陈林 / 101','李明 / 103'],['周六','何涛 / 106','赵海 / 102','王宁 / 104'],
      ['周日','陈林 / 101','王宁 / 104','何涛 / 106']]
for ri,row in enumerate([headers]+rows):
    yy=y+ri*89
    d.rectangle((x+62,yy,x+962,yy+89),fill=(177,190,167) if ri==0 else ((221,220,199) if ri%2 else (207,212,190)),outline=(116,125,103),width=2)
    for ci,text in enumerate(row):
        d.line((x+columns[ci],yy,x+columns[ci],yy+89),fill=(116,125,103),width=2)
        d.text((x+columns[ci]+12,yy+25),text,font=font(27 if ci else 32),fill=(32,51,40))
y+=8*89+37
y=section(x,y,'交接与责任', ['提前 10 分钟交接并签名。','记录异常：漏水、跳闸、门锁损坏。','替班须登记，不得空岗或私自换班。'])
d.text((x+65,1443),'负责人：陈林    登记簿：值班台右侧',font=font(29),fill=(75,82,66))

x,y=paper(1,'生活区管理规定','员工宿舍 101–106 / 公共设施使用须知')
y=section(x,y,'作息与秩序', ['06:30 起床；22:30 后保持安静。','夜班人员休息时请轻声开关门。','访客在值班台登记，21:00 前离开。'])
y=section(x,y,'床位与物品', ['床位固定，调换须向管理员登记。','个人物品入柜，贵重物品自行保管。','床梯、门洞及通道不得堆放杂物。'])
y=section(x,y,'用电与设施', ['禁止私接电线及使用大功率电炉。','离房关灯；充电设备不得放在床上。','门锁、家具损坏请登记，勿擅自拆改。'])
y=section(x,y,'报修与应急', ['供水异常：先关闭最近的支路阀门。','火情先疏散，集合点为生活区出口。','值班台分机 201；设施报修分机 206。'])
d.text((x+65,1443),'管理处签发 / 每周一更新 / 住户共同维护',font=font(28),fill=(75,82,66))

x,y=paper(2,'卫生与淋浴要求','干湿分区 / 保持排水通畅 / 防止滑倒')
y=section(x,y,'宿舍与公共区', ['每日 07:00、19:00 清扫公共通道。','垃圾分类入桶，晚班负责清运。','床单每周更换；湿衣物不得盖在灯上。'])
y=section(x,y,'更衣与洗浴', ['更衣柜内保持干燥，鞋放指定区域。','淋浴开放：06:00–08:00 / 17:00–22:00。','单次不超过 15 分钟；使用后关阀。'])
y=section(x,y,'毛巾与洗手台', ['毛巾个人专用；用后展开挂回杆上。','洗手台勿倾倒油脂、剩饭和清洁残渣。','洗衣篮仅收待洗布品，请勿投入垃圾。'])
y=section(x,y,'地漏与消毒', ['值班人员每日清理格栅内毛发、杂物。','排水慢或返水立即登记，暂停该隔间。','周三、周日 20:00 统一消毒与检查。'])
d.text((x+65,1443),'卫生负责人：王宁 / 湿区行走请注意脚下',font=font(29),fill=(75,82,66))

x,y=paper(3,'员工活动时间表','活动区预约 / 不影响轮班休息')
y=section(x,y,'每日开放时间', ['茶水与用餐 06:00–22:00','电视与阅读 12:00–14:00 / 18:00–21:30','台球与乒乓球 18:00–21:00','21:30 整理器材；22:00 关闭活动区。'])
y=section(x,y,'本周活动', ['周二 19:00 乒乓球自由练习','周四 19:30 台球交流 / 两人一组','周六 18:30 员工联谊 / 值班台报名','周日 20:00 公共区清洁 / 30 分钟'])
y=section(x,y,'使用与预约', ['预约每轮 30 分钟，不得长时间占用。','球杆与球拍用后归架；桌面禁止放杯。','餐具自行清洗，冰箱物品标注姓名。','降低电视音量；禁止在室内吸烟。'])
d.text((x+65,1443),'活动负责人：李明 / 器材损坏请及时报修',font=font(29),fill=(75,82,66))

d.rectangle((20,1570,3020,1810),fill=(52,79,66),outline=(151,158,130),width=5)
d.text((1515,1635),'员工生活区 · 公共事务与值班公告',font=font(83),fill=(236,230,203),anchor='mm')
d.text((1515,1750),'STAFF QUARTERS / DUTY · HOUSE RULES · HYGIENE · RECREATION',font=font(35),fill=(183,194,161),anchor='mm')
d.rectangle((3070,1570,4070,1970),fill=(203,177,116),outline=(118,99,62),width=4)
d.text((3132,1602),'本周提醒',font=font(59),fill=(77,65,38))
for j,text in enumerate(['周三 / 周日统一消毒','发现漏水先关支路阀门','21:30 后请降低活动音量','出口及床梯请保持畅通']):
    d.text((3132,1694+j*60),text,font=font(34),fill=(68,61,39))
im.save(OUT/'T_Staff_Notices_V3_BaseColor.png')
(OUT/'notice-atlas.json').write_text(json.dumps(dict(size=[4096,2048],pages=pages,
    header=[20,1570,3020,1810],reminder=[3070,1570,4070,1970],font='Microsoft YaHei; raster only',
    content='Real roster, rules, hygiene and recreation text; no placeholder strokes'),ensure_ascii=False,indent=2),encoding='utf8')
print('STAFF_NOTICE_TEXT_AUTHORED')
