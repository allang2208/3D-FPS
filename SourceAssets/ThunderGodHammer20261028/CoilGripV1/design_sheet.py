from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parent
sheet=Image.new('RGB',(2260,1850),(18,23,31));draw=ImageDraw.Draw(sheet)
font='C:/Windows/Fonts/msyh.ttc'
def label(x,y,text,size=28,color=(202,213,224)):
    draw.text((x,y),text,font=ImageFont.truetype(font,size),fill=color)
label(65,36,'线圈  /  COIL',58)
label(65,115,'雷神之锤专属握柄 · 三视结构设计',27)
for i,(name,title) in enumerate([('Front','正视'),('Side','侧视'),('Rear','背视')]):
    img=Image.open(P/'Design'/(name+'.png')).convert('RGB')
    sheet.paste(img,(25+i*440,195))
    label(190+i*440,163,title,25)
macro=Image.open(P/'Design/CoilDetail.png').convert('RGB').resize((860,860),Image.Resampling.LANCZOS)
sheet.paste(macro,(1380,195))
label(1420,1110,'上部闭合感应线圈',36)
for i,line in enumerate(['连续铜绕组 / 钛合金保护肋','蓝白导光槽 / 嵌入式铜接点','六段绝缘握持 / 原装端面连接','总长约 490 mm · 握持直径约 31 mm']):label(1420,1190+i*66,line,26)
label(1420,1510,'制作细化：',27)
label(1420,1575,'拉丝金属、绝缘微纹、刻线与法线贴图',24)
label(1420,1660,'Blender 结构设计稿，非游戏截图',23,(130,151,170))
sheet.save(P/'Design/Coil_ThreeViews.png')
