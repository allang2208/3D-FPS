"""Encode the fitted authoring poses as a six-chair offline preview."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]/'SourceAssets/FurnitureRest20261022/ChairReuse20261024/PreviewFinal'
labels = {'Chair': '普通椅', 'Chair50': '会客椅', 'Chair52': '办公椅',
          'Chair53': '训练凳', 'Chair55': '候诊椅', 'Bench': '更衣长凳'}
phases = {'Enter': '入座', 'Idle': '坐稳', 'Exit': '起身'}
font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 17)
small = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 14)
paths = {k: sorted((ROOT/'frames'/k).glob('*.png')) for k in labels}
timeline = {k: json.loads((ROOT/(k+'_timeline.json')).read_text()) for k in labels}
sequence = []
for index in range(len(next(iter(paths.values())))):
    im = Image.new('RGB', (960, 700), (29, 35, 42))
    draw = ImageDraw.Draw(im)
    for i, (kind, title) in enumerate(labels.items()):
        x, y = (i % 3)*320, (i//3)*340
        panel = Image.open(paths[kind][index]).convert('RGB').resize((320, 320), Image.Resampling.LANCZOS)
        im.paste(panel, (x, y+22))
        draw.text((x+8, y+2), title+' · '+phases[timeline[kind][index][0]], font=font, fill='white')
    draw.text((10, 682), 'Jason 作者姿态 · 项目家具几何 · 离线预览', font=small, fill=(204, 211, 222))
    sequence.append(im)
palette = sequence[len(sequence)//2].quantize(colors=192)
encoded = [im.quantize(palette=palette, dither=Image.Dither.NONE) for im in sequence]
encoded[0].save(ROOT/'chair_reuse.gif', save_all=True, append_images=encoded[1:],
                duration=[90 if i % 3 == 2 else 80 for i in range(len(encoded))],
                loop=0, disposal=2, optimize=True)
sequence[30].save(ROOT/'chair_reuse_contact.jpg', quality=92)
sequence[-39].save(ROOT/'chair_reuse_seated.jpg', quality=92)
print('CHAIR_REUSE_GIF', ROOT/'chair_reuse.gif')
