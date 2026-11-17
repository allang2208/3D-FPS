"""Compose same-camera engine captures; no exposure or effect image edits."""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[2]/'SourceAssets/MeteorVisualReview20261114'
def pair(frame, size=(640,360)):
    result=Image.new('RGB',(size[0]*2,size[1]+32),'#151719')
    draw=ImageDraw.Draw(result)
    for i,(folder,label) in enumerate([('Before','BEFORE'),('Final','REVISED')]):
        capture=Image.open(ROOT/folder/f'impact-{frame:04d}.png').convert('RGB').resize(size)
        result.paste(capture,(i*size[0],32))
        draw.text((i*size[0]+10,9),f'{label}  |  impact +{(frame+1)/60:.3f}s',fill='white')
    return result

samples=[3,8,23,35,50]
sheet=Image.new('RGB',(1280,392*len(samples)))
for row,index in enumerate(samples):sheet.paste(pair(index),(0,row*392))
sheet.save(ROOT/'before-after.jpg',quality=94)
frames=[pair(index,(480,270)) for index in range(0,150,2)]
frames[0].save(ROOT/'before-after.gif',save_all=True,append_images=frames[1:],duration=[33,34,33]*25,loop=0,optimize=False)
print(ROOT/'before-after.gif')
