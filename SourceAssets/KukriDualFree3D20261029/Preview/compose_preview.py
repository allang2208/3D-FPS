"""Compose synchronized front/side GIFs and key-pose sheets for inspection."""
from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont
OUT=Path(__file__).resolve().parent
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20)
small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',15)
source=json.loads((OUT/'saved-poses.json').read_text())
for number,role in enumerate(('Dual.Slash1','Dual.Slash2'),1):
    data=source['clips'][role];frames=[]
    for k,time in enumerate(data['times']):
        canvas=Image.new('RGB',(960,618),(17,23,32));draw=ImageDraw.Draw(canvas)
        draw.text((18,10),f'第 {number} 段 · Jason 双持 · 已保存动画 / 原速',font=font,fill=(235,239,245))
        draw.text((18,40),'主手蓝色 / 副手橙色       正面偏侧',font=small,fill=(185,198,214))
        draw.text((505,40),f'侧面                             {time:.2f} 秒',font=small,fill=(185,198,214))
        for x,view in [(0,'front'),(480,'side')]:
            with Image.open(OUT/'Frames'/f'{role}-{view}-{k:03d}.png') as im:canvas.paste(im.convert('RGB'),(x,70))
        frames.append(canvas)
    # A shared palette prevents frame-to-frame changes in the neutral surface.
    palette=frames[0].quantize(colors=128,method=Image.Quantize.MEDIANCUT)
    indexed=[f.quantize(palette=palette,dither=Image.Dither.NONE) for f in frames]
    durations=[50]*len(frames);durations[0]=300;durations[-1]=600
    indexed[0].save(OUT/f'Jason-Dual-Slash{number}.gif',save_all=True,append_images=indexed[1:],duration=durations,loop=0,optimize=False,disposal=2)
    selected=[min(range(len(data['times'])),key=lambda i:abs(data['times'][i]-t)) for t in (0,.15,.35,.50,.70,.85,1.05,1.30,1.55,data['duration'])]
    sheet=Image.new('RGB',(1440,5*464),(17,23,32))
    for j,k in enumerate(selected):
        thumb=frames[k].resize((720,464),Image.Resampling.LANCZOS);sheet.paste(thumb,((j%2)*720,(j//2)*464))
    sheet.save(OUT/f'Jason-Dual-Slash{number}-keyposes.jpg',quality=88)
    print('PREVIEW_GIF',OUT/f'Jason-Dual-Slash{number}.gif')
