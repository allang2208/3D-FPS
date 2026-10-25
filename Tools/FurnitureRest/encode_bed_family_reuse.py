"""A compact comparison of saved native entry motion on the five bed families."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
OUT=Path(__file__).resolve().parents[2]/'SourceAssets/FurnitureRest20261022'/globals().get('FURNITURE_REVISION','BedFamilyReuse20261024')/globals().get('REVIEW_SUBDIR','ReviewSaved')
kinds=[('Bed','普通双人床'),('BedKing','大床'),('Hospital','医院病床'),('Ward','隔离病房床'),('Bunk','上下铺 · 下铺')]
timelines={k:json.loads((OUT/(k+'_timeline.json')).read_text()) for k,_ in kinds}
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18);small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',15)
entries=[i for i,(p,t) in enumerate(timelines['Bed']) if p=='Enter'];frames=[]
for i in entries:
    canvas=Image.new('RGB',(1200,830),(29,35,42));draw=ImageDraw.Draw(canvas)
    for j,(kind,label) in enumerate(kinds):
        im=Image.open(OUT/'frames'/kind/f'{i:04d}.png').convert('RGB').resize((400,400),Image.Resampling.LANCZOS)
        x=(j%3)*400;y=(j//3)*400;canvas.paste(im,(x,y));draw.text((x+9,y+8),label,font=font,fill='white')
    draw.text((815,470),'同一套撑床、收腿节奏',font=font,fill='white')
    draw.text((815,505),'按床沿、枕头与净空适配',font=font,fill='white')
    draw.text((815,540),f'上床动作 {timelines["Bed"][i][1]:.2f}s / 3.3s',font=font,fill='white')
    caption='制作源动作 · 离线预览 · 待保存接入' if globals().get('SOURCE_PREVIEW',False) else 'UE 已保存动作 · 项目角色与床模型 · 离线预览'
    draw.text((12,806),caption,font=small,fill=(204,211,222));frames.append(canvas)
palette=frames[len(frames)//2].quantize(colors=192);frames=[f.quantize(palette=palette,dither=Image.Dither.NONE) for f in frames]
frames[0].save(OUT/'bed_family_entry.gif',save_all=True,append_images=frames[1:],duration=[90 if i%3==2 else 80 for i in range(len(frames))],loop=0,disposal=2,optimize=True)
print('BED_FAMILY_PREVIEW',OUT/'bed_family_entry.gif')
