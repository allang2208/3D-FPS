"""Pair identical live idle views before and after the handguard correction."""
import sys, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
here=Path(__file__).resolve().parent
runs=here/'WireRuns'
old=runs/'20261111-184822'
new=Path(sys.argv[1])
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',21)
sheet=Image.new('RGB',(1120,684),'#22252a')
draw=ImageDraw.Draw(sheet)
for y,(root,label) in enumerate([(old,'修正前'),(new,'修正后')]):
    v=root/'host/Visual'
    for x,(sub,tag,view) in enumerate([('Close','掌侧','_0'),('Close','指侧','_1'),('Owner','玩家视角','')]):
        data=[json.loads(l) for l in (v/(sub.lower()+'.jsonl')).read_text().splitlines()]
        matches=[a for a in data if a['case']==0 and a['stage']==1 and Path(a['image']).stem.endswith(view)]
        a=min(matches,key=lambda a:abs(a['stage_time']-3))
        im=Image.open(v/sub/a['image']).convert('RGB')
        im.thumbnail((364,302))
        sheet.paste(im,(374*x+(364-im.width)//2,y*342+38+(302-im.height)//2))
        draw.text((374*x+10,y*342+5),f'{label}  ·  {tag}',font=font,fill='white')
sheet.save(new/'handguard-compare.jpg',quality=94)
