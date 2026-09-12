from pathlib import Path
from PIL import Image,ImageDraw
import json
R=Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedMiner20260912/Reference/CMU')
for p in R.glob('*-review.json'):
    report=json.loads(p.read_text());clip=report['source_clip'];frames=[]
    for i,row in enumerate(report['samples']):
        im=Image.open(R/'Previews'/clip/f'{i:04d}.png').convert('RGB');ImageDraw.Draw(im).text((10,10),f'CMU {clip} | {row["time"]:.2f}s',(250,250,250));frames.append(im)
    frames[0].save(R/(clip+'-source.gif'),save_all=True,append_images=frames[1:],duration=250,loop=0)
    sheet=Image.new('RGB',(1260,2080),(24,26,29))
    for j in range(12):sheet.paste(frames[round(j*(len(frames)-1)/11)],((j%3)*420,(j//3)*520))
    sheet.save(R/(clip+'-sheet.jpg'),quality=92)
print('CMU_SOURCE_PREVIEWS_PACKAGED')
