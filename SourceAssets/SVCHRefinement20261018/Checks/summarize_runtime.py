"""Summarize captured real-game states; make contact sheets for visual review."""
import json,sys
from pathlib import Path
from collections import Counter
from PIL import Image,ImageDraw
P=Path(__file__).resolve().parents[3]
label=sys.argv[1]
O=P/'Saved/SVCHPoseAudit'/label
rows=[json.loads(s) for s in (O/'frames.jsonl').read_text(encoding='utf-8-sig').splitlines() if s.strip()]
summary={'completion':json.loads((O/'completion.json').read_text()),'stages':dict(Counter(r['stage'] for r in rows)),
         'meshes':sorted(set(r['mesh'] for r in rows)),'profiles':sorted(set(r['grip_profile'] for r in rows)),
         'missing_images':[r['image'] for r in rows if not (O/'Frames'/r['image']).exists()]}
for stage in summary['stages']:
    sr=[r for r in rows if r['stage']==stage]
    summary[stage]={'ammo':sorted(set(r['ammo'] for r in sr)),
                    'action_time':[min(r['action_time'] for r in sr),max(r['action_time'] for r in sr)],
                    'last':sr[-1]}
(O/'summary.json').write_text(json.dumps(summary,indent=1))
targets=[('hip',1),('ads',1.5),('reload_normal',1.3),('reload_normal',2.4),('reload_empty',2.7),('ads_return',1.5),('inspect',1.2),('inspect',3.7)]
selected=[]
for stage,time in targets:
    candidates=[r for r in rows if r['stage']==stage and (O/'Frames'/r['image']).exists()]
    if candidates:selected.append(min(candidates,key=lambda r:abs(r['stage_time']-time)))
sheet=Image.new('RGB',(1280,396*((len(selected)+1)//2)),(28,29,32));draw=ImageDraw.Draw(sheet)
for i,row in enumerate(selected):
    img=Image.open(O/'Frames'/row['image']).convert('RGB');img.thumbnail((640,360))
    x,y=(i%2)*640,(i//2)*396
    sheet.paste(img,(x,y+30));draw.text((x+10,y+7),f"{row['stage']} {row['stage_time']:.2f}s / ammo {row['ammo']}",fill='white')
sheet.save(O/'contact_sheet.jpg',quality=88)
print(json.dumps({k:summary[k] for k in ('completion','stages','meshes','profiles','missing_images')},indent=1))
