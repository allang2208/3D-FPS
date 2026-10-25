"""Encode the saved native exit pose preview at its actual playback rate."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
OUT=Path(__file__).resolve().parents[2]/'SourceAssets/FurnitureRest20261022/ApartmentReverseExit20261024/ReviewSaved'
timeline=json.loads((OUT/'ApartmentBed_timeline.json').read_text());frames=[]
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',19);small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',15)
for i,(phase,t) in enumerate(timeline):
    if phase!='Exit':continue
    im=Image.new('RGB',(600,655),(29,35,42));im.paste(Image.open(OUT/'frames/ApartmentBed'/f'{i:04d}.png').convert('RGB'),(0,30));draw=ImageDraw.Draw(im)
    draw.text((12,3),f'上床动作倒放 · 下床 {t:.2f}s / 3.4s',font=font,fill='white')
    draw.text((12,633),'UE 已保存动作 · 项目角色与床模型 · 离线预览',font=small,fill=(204,211,222));frames.append(im)
palette=frames[len(frames)//2].quantize(colors=192);frames=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in frames]
durations=[90 if i%3==2 else 80 for i in range(len(frames))];durations[-1]+=3400-sum(durations)
frames[0].save(OUT/'bed_exit.gif',save_all=True,append_images=frames[1:],duration=durations,loop=0,disposal=2,optimize=True)
print('REVERSE_EXIT_PREVIEW',OUT/'bed_exit.gif')
