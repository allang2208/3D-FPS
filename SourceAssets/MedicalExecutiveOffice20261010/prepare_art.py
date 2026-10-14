"""Original fictional medical book covers, document forms and computer UI textures."""
from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'Authored/Textures';OUT.mkdir(parents=True,exist_ok=True)
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',n)
mono=lambda n:ImageFont.truetype('C:/Windows/Fonts/consola.ttf',n)
im=Image.new('RGB',(2048,2048),(215,219,212));d=ImageDraw.Draw(im);regions={}
for i,(title,sub,col) in enumerate([('临床医学','CLINICAL MEDICINE',(32,74,84)),('诊断学','DIAGNOSTIC ATLAS',(83,50,49)),('内科学','INTERNAL MEDICINE',(52,72,62))]):
 x=16+i*512;y=16;w=480;h=640;regions['Book'+str(i)]=[x,y,w,h]
 d.rounded_rectangle((x,y,x+w,y+h),8,fill=col)
 d.line((x+24,y+24,x+24,y+h-24),fill=(175,153,102),width=3)
 d.text((x+49,y+66),title,font=font(56),fill=(227,220,196));d.text((x+50,y+155),sub,font=mono(21),fill=(177,189,174))
 d.line((x+50,y+210,x+w-50,y+210),fill=(173,154,111),width=3)
 for j in range(10):
  xx=x+145+j*17;d.line((xx,y+315,xx+55,y+405),fill=tuple(min(255,c+30) for c in col),width=3)
 d.text((x+50,y+505),'医疗参考丛书',font=font(29),fill=(219,215,191));d.text((x+50,y+562),'REFERENCE  /  VOL. '+str(i+1),font=mono(21),fill=(184,186,169))
 regions['Spine'+str(i)]=[x,684,480,80]
 d.rectangle((x,684,x+480,764),fill=col);d.text((x+22,700),title+'  /  '+str(i+1).zfill(2),font=font(32),fill=(224,218,189))
regions['Form']=[16,800,630,890]
d.rectangle((16,800,646,1690),fill=(230,229,213));d.text((58,842),'门诊记录 / CLINIC',font=font(34),fill=(45,70,65))
d.text((59,905),'随访记录    科室：全科',font=font(23),fill=(65,82,77))
for j in range(18):d.line((58,967+j*35,601,967+j*35),fill=(151,165,154),width=1)
for j,title in enumerate(['病史摘要','体征与观察','检查记录','后续安排']):d.text((59,960+j*140),title,font=font(19),fill=(83,110,100))
regions['Nameplate']=[704,820,1120,224]
d.rectangle((704,820,1824,1044),fill=(35,49,52));d.text((752,857),'医师办公席',font=font(63),fill=(221,213,183));d.text((1240,925),'CLINICAL OFFICE',font=mono(30),fill=(160,177,174))
regions['Planner']=[704,1100,800,560]
d.rectangle((704,1100,1504,1660),fill=(227,225,209));d.text((752,1140),'诊疗安排 / WORK PLAN',font=font(34),fill=(54,80,76))
for x in range(752,1470,100):d.line((x,1210,x,1600),fill=(162,172,154),width=2)
for y in range(1210,1610,78):d.line((752,y,1452,y),fill=(162,172,154),width=2)
im.save(OUT/'T_MedicalOffice_Print.png')
(ROOT/'Config/atlas.json').write_text(json.dumps({'size':[2048,2048],'regions':regions},ensure_ascii=False,indent=2),encoding='utf8')
# Retain the monitor's existing UV rectangle; the rest remains the local source atlas.
src=ROOT.parent/'StationWorkshop20261003/Authored/T_Workshop_PrintAtlas.png'
im=Image.open(src).convert('RGB');d=ImageDraw.Draw(im)
x,y,w,h=1240,16,784,441
d.rectangle((x,y,x+w,y+h),fill=(14,27,34));d.rectangle((x+8,y+8,x+w-8,y+59),fill=(32,68,73))
d.text((x+25,y+19),'CLINIC  /  WORKSPACE',font=mono(26),fill=(189,218,210))
d.rectangle((x+17,y+80,x+165,y+h-20),fill=(22,43,49))
for i,t in enumerate(['今日门诊','诊疗记录','医学资料','检查申请','工作日历']):d.text((x+30,y+102+i*56),t,font=font(19),fill=(163,190,185))
d.text((x+193,y+87),'门诊工作台',font=font(27),fill=(206,218,201))
for i,t in enumerate(['09:00   门诊 / 已登记','09:30   复诊 / 待接诊','10:00   随访 / 已预约']):
 yy=y+139+i*47;d.rectangle((x+192,yy-5,x+751,yy+34),fill=(26+i*3,44+i*3,52+i*3));d.text((x+207,yy),t,font=font(20),fill=(159,189,186))
d.text((x+195,y+298),'科室资料  ·  交班记录  ·  设备状态',font=font(19),fill=(118,155,160))
d.line((x+198,y+367,x+749,y+367),fill=(63,90,95),width=2)
d.text((x+199,y+386),'LOCAL RECORDS  /  MEDICAL SERVICES',font=mono(16),fill=(99,155,145))
im.save(OUT/'T_MedicalOffice_Screen.png')
print('MEDICAL_EXECUTIVE_PRINT_ART_SAVED')
