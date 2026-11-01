"""Lay out the requested real model previews without retouching the renders."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
P=Path(__file__).resolve().parent;V=P/'Previews'
def f(n):return ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',n)
def label(d,text,x,y,size=32):d.text((x,y),text,font=f(size),fill=(213,218,224))
def place(board,name,box):
 im=Image.open(V/name).convert('RGB');im.thumbnail((box[2]-box[0],box[3]-box[1]),Image.Resampling.LANCZOS)
 board.paste(im,(int((box[0]+box[2]-im.width)/2),int((box[1]+box[3]-im.height)/2)))
board=Image.new('RGB',(2400,1910),(18,23,28));d=ImageDraw.Draw(board)
label(d,'贯雷锤座 V12｜闭合锻冠',55,28,52)
label(d,'实际模型渲染 · 连续顶部结构 · 4K 金属法线与粗糙度贴图',57,102,28)
place(board,'04_threequarter.png',(25,155,1205,1400))
label(d,'两侧流线连成顶部锻冠',65,1410,31)
place(board,'09_crown_detail.png',(1230,155,2375,900))
label(d,'冠顶编纹、连续凹槽与嵌银细节',1260,910,30)
place(board,'10_top.png',(1230,975,2375,1715))
label(d,'俯视 · 顶部完整闭合',1260,1735,30)
label(d,'原厂符印与安装接口保留',65,1510,28)
label(d,'钢体 / 银饰 / 凹槽 / 嵌纹分材质处理',65,1560,28)
label(d,'4 组 4096² BaseColor + ORM + Normal',65,1610,28)
label(d,'独立检查稿，尚未替换游戏资产',65,1810,27)
board.save(V/'GuanLei_V12_ClosedCrown.png')
overview=Image.new('RGB',(2400,2160),(18,23,28));d=ImageDraw.Draw(overview)
label(d,'贯雷锤座 V12｜结构与装配',55,25,52)
label(d,'正、侧、背视图及原厂锤头装配 · Blender 实体渲染',57,96,27)
for i,(file,title) in enumerate([('01_front.png','正面'),('02_side.png','侧面 · 安装接触面'),('03_back.png','背面')]):
 x=30+i*790;place(overview,file,(x,150,x+760,1035));label(d,title,x+25,1047,34)
d.line((50,1110,2350,1110),fill=(65,73,82),width=2)
place(overview,'05_assembly.png',(30,1140,1540,2070));label(d,'与原厂锤头、柄颈装配',70,2080,34)
place(overview,'08_geometry.png',(1560,1150,2370,2040));label(d,'无贴图几何视图',1600,2080,34)
overview.save(V/'GuanLei_V12_Assembly.png')
manifest=json.loads((P/'model_manifest.json').read_text(encoding='utf-8'))
manifest['preview_views']=[str(p) for p in sorted(V.glob('0*.png'))]+[str(V/'10_top.png')]
manifest['purpose']='High-resolution authoring candidate for user inspection; not runtime LOD or game publication'
manifest['top_surface']='Closed crown with independent two-dimensional UV strip and seated interlaced silver ornament'
(P/'model_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('V12_PREVIEW_SHEETS_SAVED')
