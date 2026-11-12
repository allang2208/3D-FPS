"""Reinspect the matching-asset real-clock network run. No runtime invocation."""
from pathlib import Path
import json,sys
from collections import defaultdict
from PIL import Image, ImageDraw

HERE=Path(__file__).resolve().parent
RUN=Path(sys.argv[1])
out=HERE/'remote';out.mkdir(exist_ok=True)
names=['base','vertical','tactical_vertical','angled','canted','prism']
summary={}
for peer in ['host','client']:
    root=RUN/peer/'Visual'
    rows=[json.loads(s) for s in (root/'remote.jsonl').read_text().splitlines()]
    groups=defaultdict(list)
    for row in rows:
        if row.get('profile','').startswith('/Game/Weapons/M249/'):
            groups[row['weapon_instance']].append(row)
    picked=[];info=[]
    for case,(instance,part) in enumerate(groups.items()):
        end=max(i for i,x in enumerate(part) if x['action'] in (2,3))
        anchor=part[end]['time']
        chosen=[min(part,key=lambda x:abs(x['time']-(anchor+dt))) for dt in [-.4,0,.2,.6,1.2,2.]]
        chosen.append(part[-1])
        picked.extend((case,x) for x in chosen)
        info.append(dict(case=case,instance=instance,tail_frames=len(part)-end-1,
                         tail_seconds=part[-1]['time']-anchor,
                         tail_actions=sorted({x['action'] for x in part[end+1:]})))
    for page in range(4):
        selected=picked[page*21:(page+1)*21]
        # Three cases per page; seven sequential frames per case. Originals retained.
        canvas=Image.new('RGB',(7*300,3*324),'#202020');draw=ImageDraw.Draw(canvas)
        for i,(case,row) in enumerate(selected):
            im=Image.open(root/'Remote'/row['image']).convert('RGB');im.thumbnail((300,300))
            x=(i%7)*300;y=(i//7)*324;canvas.paste(im,(x,y+24))
            draw.text((x+3,y+4),f'{names[case//2]} {"empty" if case%2 else "normal"} {row["time"]:.2f} a={row["action"]}',fill='white')
        canvas.save(out/f'{peer}_tails_{page}.jpg',quality=93)
    summary[peer]=info
(HERE/'remote_tail_review.json').write_text(json.dumps(dict(run=str(RUN),peers=summary),indent=2))
print('Packaged 24 matching-asset remote endings, seven frames each.')
