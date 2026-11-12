"""Pair source times in the earlier and revised PKM player viewport."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,sys
run=Path(sys.argv[1]);here=Path(__file__).resolve().parent
old=here/'WireRuns/20261111-191307'
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
sheet=Image.new('RGB',(1224,800),'#202329');draw=ImageDraw.Draw(sheet)
for i,(case,root,version) in enumerate([(6,old,'修正前'),(6,run,'修正后'),(7,old,'修正前'),(7,run,'修正后')]):
    seq=[]
    for peer in ['host','client']:
        v=root/peer/'Visual'
        for row in map(json.loads,(v/'owner.jsonl').read_text().splitlines()):
            if row['case']==case and row['stage']==3 and (v/'Owner'/row['image']).is_file():
                seq.append((row,v/'Owner'/row['image']))
    for x,t in enumerate([.47,.62,.88,1.38]):
        row,file=min(seq,key=lambda a:abs(a[0]['source_time']-t));im=Image.open(file).convert('RGB').resize((302,169))
        sheet.paste(im,(306*x,i*200+30)); draw.text((306*x+4,200*i+3),f'{version} · '+('空仓' if case%2 else '普通')+ f'  {row["source_time"]:.2f} s',font=font,fill='white')
sheet.save(run/'pkm-reload-compare.jpg',quality=94)
