"""Two synchronized views of the saved sofa takes, for the requested GIF."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FurnitureRest20261022/RelaxedSeatV5/ReviewSaved')
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',23)
small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',17)
labels={'Sofa':'中间座位 · 双手放松搭腿','SofaLeft':'扶手座位 · 一手搭扶手'}
phases={'Enter':'坐入','Idle':'坐稳','Exit':'起身'}
frames={};timelines={}
for kind in labels:
    frames[kind]=sorted((ROOT/'frames'/kind).glob('*.png'))
    timelines[kind]=json.loads((ROOT/(kind+'_timeline.json')).read_text())
sequence=[]
for i in range(max(map(len,frames.values()))):
    im=Image.new('RGB',(1200,660),(29,35,42));draw=ImageDraw.Draw(im)
    for col,kind in enumerate(labels):
        idx=min(i,len(frames[kind])-1)
        im.paste(Image.open(frames[kind][idx]).convert('RGB'),(col*600,42))
        draw.text((col*600+16,8),labels[kind]+' · '+phases[timelines[kind][idx][0]],font=font,fill=(239,243,248))
        draw.text((col*600+16,634),'已保存动作 · 中性材质离线预览',font=small,fill=(204,211,222))
    sequence.append(im.resize((1000,550),Image.Resampling.LANCZOS))
palette=sequence[len(sequence)//2].quantize(colors=192)
q=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in sequence]
q[0].save(ROOT/'relaxed_sitting.gif',save_all=True,append_images=q[1:],duration=[80 if i%3!=2 else 90 for i in range(len(q))],loop=0,disposal=2,optimize=True)
sheet=Image.new('RGB',(1500,1100),(29,35,42))
for row,phase in enumerate(('Enter','Exit')):
    ids=[i for i,(p,t) in enumerate(timelines['SofaLeft']) if p==phase]
    for col,j in enumerate([ids[0],ids[len(ids)//4],ids[len(ids)//2],ids[3*len(ids)//4],ids[-1]]):
        # Keep the support hand visible in the review contact sheet.
        panel=Image.open(frames['SofaLeft'][j]).convert('RGB').resize((300,300))
        sheet.paste(panel,(col*300,row*550+40))
        panel=Image.open(frames['Sofa'][j]).convert('RGB').resize((300,300))
        sheet.paste(panel,(col*300,row*550+300))
        ImageDraw.Draw(sheet).text((col*300+8,row*550+8),phases[phase]+f' {timelines["SofaLeft"][j][1]:.2f}s',font=font,fill=(240,243,248))
sheet.save(ROOT/'transition_sheet.jpg',quality=93)
print('RELAXED_SEAT_GIF',ROOT/'relaxed_sitting.gif')
