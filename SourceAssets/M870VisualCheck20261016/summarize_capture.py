import json,sys
from pathlib import Path
from collections import Counter
from PIL import Image,ImageDraw
O=Path(__file__).parent
R=O.parents[1]/'Saved/M870PoseAudit'/sys.argv[1]
rows=[json.loads(x) for x in (R/'frames.jsonl').read_text(encoding='utf-8-sig').splitlines()]
rows=[x for x in rows if (R/'Frames'/x['image']).exists()]
out=R/'Review';out.mkdir(exist_ok=True)
summary={'frames_on_disk':len(rows),'groups':{},'sheets':[]}
for wardrobe in ('bare','chainmail'):
 for stage in ('hip','ads','reload_normal','reload_empty','ads_return'):
  g=[x for x in rows if x['wardrobe']==wardrobe and x['stage']==stage]
  summary['groups'][wardrobe+'_'+stage]={'frames':len(g),'aim_range':[min(x['aim_alpha'] for x in g),max(x['aim_alpha'] for x in g)] if g else [],'actions':dict(Counter(x['action'] for x in g)),'ammo':sorted(set(x['ammo'] for x in g)),'components':sorted(set(c['asset'] for x in g for c in x['visible_components']))}
def choose(wardrobe,stage,time,clock='stage_time'):
 g=[x for x in rows if x['wardrobe']==wardrobe and x['stage']==stage]
 if clock=='action_time':g=[x for x in g if x['action_alpha']>.95]
 return min(g,key=lambda x:abs(x[clock]-time))
def sheet(name,selected,cols=2,width=640):
 h=width*9//16;canvas=Image.new('RGB',(cols*width,((len(selected)+cols-1)//cols)*(h+28)),(24,24,24));draw=ImageDraw.Draw(canvas)
 for i,row in enumerate(selected):
  im=Image.open(R/'Frames'/row['image']).convert('RGB');im.thumbnail((width,h))
  x=(i%cols)*width;y=(i//cols)*(h+28);canvas.paste(im,(x,y+28))
  label=f"{row['wardrobe']} {row['stage']}  t={row['action_time']:.3f}  ADS={row['aim_alpha']:.2f}  ammo={row['ammo']}"
  draw.text((x+6,y+7),label,fill=(240,240,240))
 canvas.save(out/(name+'.jpg'),quality=90)
 (out/(name+'.json')).write_text(json.dumps(selected,indent=2))
 summary['sheets'].append(str(out/(name+'.jpg')))
sheet('hip_ads',[choose(w,s,1.4) for w in ('bare','chainmail') for s in ('hip','ads')])
sheet('ads_after_reload',[choose(w,'ads_return',1.4) for w in ('bare','chainmail')])
for wardrobe in ('bare','chainmail'):
 for stage in ('reload_normal','reload_empty'):
  times=[.2,.73,1.57,2.40,3.23,4.07,5.73,6.0,6.43,6.62,6.9] if stage=='reload_empty' else [.2,.73,1.57,2.4,3.23,6.0,6.25,6.5]
  sheet(wardrobe+'_'+stage,[choose(wardrobe,stage,t,'action_time') for t in times],cols=3,width=440)
(R/'summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps({'groups':{k:{a:v[a] for a in ['frames','aim_range','ammo']} for k,v in summary['groups'].items()},'sheets':summary['sheets']},indent=2))
