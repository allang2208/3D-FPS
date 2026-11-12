from PIL import Image,ImageDraw
from pathlib import Path
import json,sys
run=Path(sys.argv[1]); seq=[]
for p in ['host','client']:
 v=run/p/'Visual'
 for q in map(json.loads,(v/'owner.jsonl').read_text().splitlines()):
    if q['case']==6 and q['stage']==3 and .27<q['source_time']<1.6:seq.append((q['source_time'],v/'Owner'/q['image']))
seq.sort();out=Image.new('RGB',(1250,158*((len(seq)+4)//5)));d=ImageDraw.Draw(out)
for j,(t,f) in enumerate(seq):
 im=Image.open(f).resize((247,139));x=j%5*250;y=j//5*158;out.paste(im,(x,y+18));d.text((x+4,y+1),f'{t:.2f}')
out.save(run/'pkm-near-frames.jpg',quality=91)
