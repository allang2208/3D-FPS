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
label(d,'疾雷锤座 V13｜聚雷锻脊 · 实际模型',55,28,52)
label(d,'上收折面锻肩 / 低冠饰 / 三路聚雷槽 / 背部 Y 形锻脊',57,100,28)
for i,(name,title) in enumerate([('01_front','正面'),('02_side','侧面 · 原厂安装端'),('03_back','背面 · 导雷锻脊')]):
 x=30+i*790;place(board,V/(name+'.png'),(x,150,x+760,1035));label(d,title,x+25,1047,34)
d.line((50,1110,2350,1110),fill=(65,73,82),width=2)
place(board,V/'05_assembly.png',(30,1140,1540,2070));label(d,'与原厂锤头、柄颈装配',70,2080,34)
place(board,V/'04_threequarter.png',(1560,1150,2370,2040));label(d,'立体轮廓与材质',1600,2080,34)
board.save(V/'JiLei_V13_Inspection.png')
detail=Image.new('RGB',(2400,1810),(18,23,28));d=ImageDraw.Draw(detail)
label(d,'疾雷锤座 V13｜结构与表面近景',55,28,52)
label(d,'实体凹槽与嵌银 · 四组 4K PBR / 法线贴图 · 独立模型检查稿',57,100,27)
place(detail,V/'04_threequarter.png',(25,160,1205,1700));label(d,'折面轮廓与实体承力厚度',65,1725,30)
place(detail,V/'09_crown_detail.png',(1230,155,2375,915));label(d,'顶部三路导雷槽与低冠饰',1260,935,30)
place(detail,V/'07_neck_detail.png',(1230,1020,2375,1690));label(d,'柄颈衔接与贴面编纹',1260,1725,30)
detail.save(V/'JiLei_V13_Details.png')
compare=Image.new('RGB',(2400,1640),(18,23,28));d=ImageDraw.Draw(compare)
label(d,'两款锤座｜相同视角与比例',55,28,52)
label(d,'实际模型渲染 · 同一原厂接口与中央符印 · 分别保留回环与聚雷特征',57,100,27)
g=Image.open(P.parent/'GuanLeiClosedCrownV12/Previews/01_front.png').convert('RGB')
g=g.resize((round(g.width*.180/.195),round(g.height*.180/.195)),Image.Resampling.LANCZOS)
common=Image.new('RGB',(1200,1400),(10,17,21));common.paste(g,((1200-g.width)//2,(1400-g.height)//2+43));common.save(V/'GuanLei_CommonScale.png')
place(compare,V/'GuanLei_CommonScale.png',(55,180,1170,1470));place(compare,V/'01_front.png',(1230,180,2345,1470))
label(d,'贯雷 V12 · 闭合回环锻冠',115,1500,39)
label(d,'疾雷 V13 · 上收折面聚雷锻脊',1265,1500,39)
compare.save(V/'GuanLei_JiLei_ModelComparison.png')
m=json.loads((P/'model_manifest.json').read_text(encoding='utf-8'))
m['preview_views']=[str(v) for v in sorted(V.glob('0*.png'))]+[str(V/'10_top.png')]
m['preview_sheets']=[str(V/n) for n in ('JiLei_V13_Inspection.png','JiLei_V13_Details.png','GuanLei_JiLei_ModelComparison.png')]
(P/'model_manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
print('JILEI_V13_SHEETS_SAVED',flush=True)
