"""Contact sheets preserve original capture colour; no exposure/image retouching."""
from pathlib import Path
from PIL import Image,ImageDraw
import sys

folder=Path(__file__).resolve().parents[3]/'SourceAssets/TemperateHillsVillage/WallReview20261114'
if '--detail' in sys.argv:folder=folder/'Detail'
dest=folder/'SheetsLit';dest.mkdir(exist_ok=True)
paths=sorted((folder/'CapturesLit').glob('wall_*.png'))
paths+=sorted((folder/'CapturesLit').glob('root_*.png'))
columns,rows=4,6
width,height=480,300
for page,start in enumerate(range(0,len(paths),columns*rows)):
    batch=paths[start:start+columns*rows]
    sheet=Image.new('RGB',(columns*width,rows*(height+24)),(230,230,230))
    draw=ImageDraw.Draw(sheet)
    for i,path in enumerate(batch):
        image=Image.open(path).convert('RGB');image.thumbnail((width,height))
        x=(i%columns)*width;y=(i//columns)*(height+24)
        sheet.paste(image,(x,y+24));draw.text((x+7,y+5),path.stem,fill=(15,15,15))
    sheet.save(dest/('sheet_%02d.jpg'%page),quality=92)
print('CAPTURES',len(paths),'SHEETS',(len(paths)+columns*rows-1)//(columns*rows))
