"""Arrange actual Blender renders for the user's requested model inspection."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
P=Path(__file__).resolve().parent;V=P/'Previews'
font='C:/Windows/Fonts/msyh.ttc'
def f(n):return ImageFont.truetype(font,n)
def place(board,name,box):
 im=Image.open(V/name).convert('RGB');im.thumbnail((box[2]-box[0],box[3]-box[1]),Image.Resampling.LANCZOS)
 board.paste(im,(int((box[0]+box[2]-im.width)/2),int((box[1]+box[3]-im.height)/2)))
def label(draw,text,x,y,size=33):draw.text((x,y),text,font=f(size),fill=(213,218,224))
board=Image.new('RGB',(2400,2160),(18,23,28));d=ImageDraw.Draw(board)
label(d,'贯雷锤座 V11｜实际模型检查稿',55,25,52)
label(d,'Blender 实体渲染 · 原厂接口与符印保留 · 尚未替换游戏模型',57,96,27)
for i,(file,title) in enumerate([('01_front.png','正面'),('02_side.png','侧面 · 安装接触面'),('03_back.png','背面')]):
 x=30+i*790;place(board,file,(x,150,x+760,1035));label(d,title,x+25,1047,34)
d.line((50,1110,2350,1110),fill=(65,73,82),width=2)
place(board,'05_assembly.png',(30,1140,1540,2070));label(d,'与原厂锤头、柄颈装配',70,2080,34)
place(board,'08_geometry.png',(1560,1150,2370,2040));label(d,'无贴图几何视图',1600,2080,34)
board.save(V/'GuanLei_V11_Inspection.png')
details=Image.new('RGB',(2400,1780),(18,23,28));d=ImageDraw.Draw(details);label(d,'贯雷锤座 V11｜结构与衔接近景',55,25,50)
place(details,'04_threequarter.png',(25,125,1200,1670));label(d,'三分之四视角',65,1690,32)
place(details,'06_shoulder_detail.png',(1230,125,2375,960));label(d,'锻肩 · 嵌银编纹 · 凹槽',1260,980,30)
place(details,'07_neck_detail.png',(1230,1040,2375,1650));label(d,'柄颈与原厂接口',1260,1690,30)
details.save(V/'GuanLei_V11_Details.png')
manifest=json.loads((P/'model_manifest.json').read_text(encoding='utf-8'));manifest['method']='New closed forged core, continuous carved shoulder surfaces, multi-strand relief; original rune relief and exact factory interface bands retained';manifest['preview_views']=[str(V/(n+'.png')) for n in ('01_front','02_side','03_back','04_threequarter','05_assembly','06_shoulder_detail','07_neck_detail','08_geometry')]
manifest['published_to_game']=False;manifest['user_accepted']=False
(P/'model_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('INSPECTION_SHEETS_SAVED',flush=True)
