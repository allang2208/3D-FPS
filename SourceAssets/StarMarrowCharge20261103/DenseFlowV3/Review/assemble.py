"""Make the review media from the commandlet's actual render-target frames."""
import csv
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parent / sys.argv[1]
font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 17)
labels = dict(charge='充能动作', idle='待机燃烧', swing='挥剑', stop='定姿急停', recover='收剑', expiry='到期熄灭')
with (root / 'frames.csv').open(encoding='utf-8-sig') as stream:
    rows = list(csv.DictReader(stream))

def frame(row):
    return Image.open(root / f"f{int(row['frame']):03}.png").convert('RGB')

def labeled(row, size):
    image = frame(row).resize((size,size), Image.Resampling.LANCZOS)
    labeled_image = Image.new('RGB',(size,size+31),(27,31,40));labeled_image.paste(image,(0,31))
    ImageDraw.Draw(labeled_image).text((10,4),f"{labels[row['phase']]}   {row['time']} s",font=font,fill=(226,219,200))
    return labeled_image

sequence = [labeled(row,440) for row in rows[::2]]
swatches=Image.new('RGB',(160,160*len(sequence[::4])))
for i,im in enumerate(sequence[::4]):
    swatches.paste(im.resize((160,160),Image.Resampling.LANCZOS),(0,i*160))
palette=swatches.quantize(colors=192,method=Image.Quantize.MEDIANCUT)
sequence=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in sequence]
sequence[0].save(root/'charged-fire.gif',save_all=True,append_images=sequence[1:],duration=[67 if i%3 else 66 for i in range(len(sequence))],loop=0,disposal=2)
sheet = Image.new('RGB',(3*320,2*351))
for slot, idx in enumerate([48,170,230,250,354,382]):
    sheet.paste(labeled(rows[idx//2],320),(slot%3*320,slot//3*351))
sheet.save(root/'keyframes.png')

stats={}
for idx in [170,250,354,382]:
    row=rows[idx//2];on=np.asarray(frame(row),dtype=np.int16);off=np.asarray(Image.open(root/f'off{idx:03}.png').convert('RGB'),dtype=np.int16)
    diff=on-off
    flame=(diff[:,:,2]>14)&(diff[:,:,2]>diff[:,:,0]+5)
    # Screen-space mask only. Compare to the same pose, lighting and camera without the effect.
    start=np.array([float(row['base_px']),float(row['base_py'])]);end=np.array([float(row['tip_px']),float(row['tip_py'])]);axis=end-start
    yy,xx=np.nonzero(flame);points=np.column_stack([xx,yy])-start
    along=points@axis/(axis@axis);across=np.abs(points[:,0]*axis[1]-points[:,1]*axis[0])/np.linalg.norm(axis)
    bands=np.histogram(along[across<.1*np.linalg.norm(axis)],bins=np.linspace(.055,.965,19))[0]
    stats[idx]=dict(blue_pixels=int(flame.sum()),length_bins_with_blue=int((bands>=3).sum()),length_bins_total=len(bands),counts=[row.get(n) for n in ['core','tongues','curls','wake','embers']])
(root/'visual-measurements.json').write_text(json.dumps(stats,indent=2));print(stats)
