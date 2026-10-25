"""Compare the old and reversed exits using the saved compressed pose renders."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FurnitureRest20261022/ReversedExitV7/ReviewSaved')
OLD=ROOT.parent.parent/'HangingEntryV6/ReviewSaved'
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',23)
small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',17)
timeline=json.loads((ROOT/'SofaLeft_timeline.json').read_text())
frames=sorted((ROOT/'frames/SofaLeft').glob('*.png'))
before=sorted((OLD/'frames/SofaLeft').glob('*.png'))
ids=[i for i,(phase,t) in enumerate(timeline) if phase=='Exit']
indices=[ids[0]]*6+ids+[ids[-1]]*3
sequence=[]
for i in indices:
    im=Image.new('RGB',(1200,650),(29,35,42));draw=ImageDraw.Draw(im)
    for col,(label,path) in enumerate((('上一版起身',before[i]),('本版：沿入座轨迹自然起身',frames[i]))):
        im.paste(Image.open(path).convert('RGB'),(col*600,42))
        draw.text((col*600+16,8),label,font=font,fill=(239,243,248))
    draw.text((16,625),'同机位 · 实际保存动作的离线对比',font=small,fill=(204,211,222))
    sequence.append(im.resize((1000,542),Image.Resampling.LANCZOS))
palette=sequence[len(sequence)//2].quantize(colors=192)
q=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in sequence]
q[0].save(ROOT/'exit_before_after.gif',save_all=True,append_images=q[1:],duration=[80 if i%3!=2 else 90 for i in range(len(q))],loop=0,disposal=2,optimize=True)
sheet=Image.new('RGB',(1500,660),(29,35,42));draw=ImageDraw.Draw(sheet)
for col,i in enumerate((ids[0],ids[len(ids)//4],ids[len(ids)//2],ids[3*len(ids)//4],ids[-1])):
    draw.text((col*300+8,5),f'{timeline[i][1]:.2f}s',font=font,fill=(239,243,248))
    for row,kind in enumerate(('SofaLeft','Sofa')):
        p=ROOT/'frames'/kind/f'{i:04d}.png'
        sheet.paste(Image.open(p).convert('RGB').resize((300,300)),(col*300,35+row*310))
sheet.save(ROOT/'exit_sheet.jpg',quality=94)
print('EXIT_COMPARISON_GIF',ROOT/'exit_before_after.gif')
