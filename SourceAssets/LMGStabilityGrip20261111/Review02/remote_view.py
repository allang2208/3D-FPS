"""Inspect the first visible remote frames of each incoming equipment instance."""
from itertools import groupby
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,sys
run=Path(sys.argv[1])
for peer in ('host','client'):
    v=run/peer/'Visual'
    source=[json.loads(s) for s in (v/'remote.jsonl').read_text().splitlines()]
    groups=[list(g) for k,g in groupby(source,lambda r:r['weapon_instance'])]
    groups=[g for g in groups if g[-1].get('profile') and any('visible_parts' in r for r in g)]
    if not groups:continue
    sheet=Image.new('RGB',(1200,180*len(groups)),'#161a20')
    draw=ImageDraw.Draw(sheet)
    for i,g in enumerate(groups):
        for n in range(min(6,len(g))):
            row=g[n]
            im=Image.open(v/'Remote'/row['image']).convert('RGB').crop((135,195,557,520))
            im.thumbnail((198,152))
            sheet.paste(im,(n*200,180*i+22))
            draw.text((n*200+3,180*i+3),f'{i}: {n} / action {row["action"]}',fill='white')
    sheet.save(run/(peer+'-remote-equip.jpg'),quality=94)
    for i,g in enumerate(groups):
        if i not in (4,5,6,7):continue
        r=g[0]
        print(peer,i,r['image'],[(p['mesh'],p['parent'],round(p.get('screen_x',0)),round(p.get('screen_y',0))) for p in r.get('visible_parts',[]) if 'Grip' in p['mesh'] or 'grip' in p['mesh']])
