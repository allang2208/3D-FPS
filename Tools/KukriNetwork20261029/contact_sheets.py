import argparse
from collections import defaultdict
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw

p=argparse.ArgumentParser()
p.add_argument('run',type=Path)
a=p.parse_args()
groups=defaultdict(list)
for f in sorted((a.run/'Frames').glob('frame_*.png')):
    groups['_'.join(f.stem.split('_')[1:-1])].append(f)
out=a.run/'Review';out.mkdir(exist_ok=True)
for key,files in groups.items():
    tiles=[]
    for f in files:
        im=Image.open(f).convert('RGB')
        im=ImageOps.contain(im,(640,360))
        tile=Image.new('RGB',(640,386),'#1a1a1a')
        tile.paste(im,((640-im.width)//2,26))
        ImageDraw.Draw(tile).text((10,7),f.stem,fill='white')
        tiles.append(tile)
    sheet=Image.new('RGB',(640*4,386*((len(tiles)+3)//4)),'#111111')
    for i,im in enumerate(tiles):sheet.paste(im,((i%4)*640,(i//4)*386))
    path=out/(key+'.jpg');sheet.save(path,quality=93)
    print(path)
