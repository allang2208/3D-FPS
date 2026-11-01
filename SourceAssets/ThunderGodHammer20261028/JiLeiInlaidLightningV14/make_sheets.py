"""Layout actual Blender renders; all geometry and material images are unretouched."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
P=Path(__file__).resolve().parent;V=P/'Previews'
def font(n):return ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',n)
def label(d,text,x,y,size=32):d.text((x,y),text,font=font(size),fill=(213,218,224))
def place(board,file,box):
 im=Image.open(file).convert('RGB');im.thumbnail((box[2]-box[0],box[3]-box[1]),Image.Resampling.LANCZOS)
 board.paste(im,(int((box[0]+box[2]-im.width)/2),int((box[1]+box[3]-im.height)/2)))
board=Image.new('RGB',(2400,2160),(18,23,28));d=ImageDraw.Draw(board)
label(d,'疾雷锤座 V14｜连续锻肩 · 内嵌雷纹',55,28,52)
label(d,'实际模型渲染 · 连续锻肩 / 渐收槽尾 / 一体汇聚纹 / 哑光嵌银',57,100,28)
for i,(name,title) in enumerate([('01_front','正面'),('02_side','侧面 · 原厂安装端'),('03_back','背面 · 导雷锻脊')]):
 x=30+i*790;place(board,V/(name+'.png'),(x,150,x+760,1035));label(d,title,x+25,1047,34)
d.line((50,1110,2350,1110),fill=(65,73,82),width=2)
place(board,V/'05_assembly.png',(30,1140,1540,2070));label(d,'与原厂锤头、柄颈装配',70,2080,34)
place(board,V/'04_threequarter.png',(1560,1150,2370,2040));label(d,'立体轮廓与材质',1600,2080,34)
board.save(V/'JiLei_V14_Inspection.png')
detail=Image.new('RGB',(2400,1810),(18,23,28));d=ImageDraw.Draw(detail)
label(d,'疾雷锤座 V14｜闪电饰纹与衔接',55,28,52)
label(d,'实际模型近景 · 连续轮廓 · 内嵌银纹与细蓝槽 · 4K 法线贴图',57,100,27)
place(detail,V/'04_threequarter.png',(25,160,1205,1700));label(d,'折面轮廓与实体承力厚度',65,1725,30)
place(detail,V/'11_lightning_joint.png',(1230,155,2375,915));label(d,'连续锻肩与槽内收口',1260,935,30)
place(detail,V/'12_rear_junction.png',(1230,1020,2375,1690));label(d,'背部 Y 形一体汇聚纹',1260,1725,30)
detail.save(V/'JiLei_V14_Details.png')
compare=Image.new('RGB',(2400,1640),(18,23,28));d=ImageDraw.Draw(compare)
label(d,'疾雷锤座｜闪电饰纹优化前后',55,28,52)
label(d,'实际模型 · 相同视角、比例与灯光 · 原厂接口与中央符印保留',57,100,27)
place(compare,P.parent/'JiLeiPrecisionV13/Previews/04_threequarter.png',(55,180,1170,1470));place(compare,V/'04_threequarter.png',(1230,180,2345,1470))
label(d,'V13 · 修改前',115,1500,39)
label(d,'V14 · 连续锻肩与内嵌雷纹',1265,1500,39)
compare.save(V/'JiLei_V13_V14_Comparison.png')
m=json.loads((P/'model_manifest.json').read_text(encoding='utf-8'))
m['preview_views']=[str(v) for v in sorted(V.glob('0*.png'))]+[str(v) for v in sorted(V.glob('1*.png'))]
m['preview_sheets']=[str(V/n) for n in ('JiLei_V14_Inspection.png','JiLei_V14_Details.png','JiLei_V13_V14_Comparison.png')]
(P/'model_manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
print('JILEI_V14_SHEETS_SAVED',flush=True)
