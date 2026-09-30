import json
from pathlib import Path
r=Path('Content/ColdSteelData')
a=r/'AttachmentIcons20260913'
rows=[]
def add(family,w,slot,id):
 key=f'{w}_category_{slot}' if id is None else f'{w}_{slot}_{id}'
 common=f'category_{slot}' if id is None else f'{slot}_{id}'
 folder={'firearm':'FramedFirearms','bow':'FramedBows'}.get(family)
 path=None
 if folder:
  if (a/folder/(key+'.png')).exists(): path=a/folder/(key+'.png')
  elif not (a/(key+'.png')).exists() and (a/folder/(common+'.png')).exists():path=a/folder/(common+'.png')
 if path is None:
  path=next((p for p in [a/(key+'.png'),a/(common+'.png')] if p.exists()),None)
 rows.append(dict(family=family,weapon=w,slot=slot,option=id or 'CATEGORY',key=key,resolved=str(path) if path else None,status='framed' if path and folder and path.parent.name==folder else 'existing_image' if path else 'fallback'))
g=json.loads((r/'gunsmith.json').read_text(encoding='utf-8-sig'))
for w in g['weapons']:
 opts={s:list(v) for s,v in w['options'].items()};slots=list(w['allowed'])
 for s,v in g.get('common_options',{}).items():
  if s not in slots:slots.append(s)
  opts.setdefault(s,[]).extend(o for o in v if o['id'] not in {p['id'] for p in opts.get(s,[])})
 if w.get('pistol_grip_surface',{}).get('mesh') and g.get('pistol_grip_surface_options'):
  opts['reargrip']=g['pistol_grip_surface_options']
  if 'reargrip' not in slots:slots.append('reargrip')
 for s in slots:
  if not any(str(o['id']).lower()!='false' for o in opts.get(s,[])):continue
  add('firearm',w['id'],s,None)
  for id in dict.fromkeys(['false']+[str(o['id']).lower() for o in opts.get(s,[])]):add('firearm',w['id'],s,id)
for f in ['bow','staff','melee','tool']:
 g=json.loads((r/(f+'-gunsmith.json')).read_text(encoding='utf-8-sig'))
 for w in g['weapons']:
  w=w['id'] if isinstance(w,dict) else w
  for c in g['columns']:
   add(f,w,c['key'],None)
   for id in dict.fromkeys(['false']+[str(o['id']).lower() for o in c.get('options',[]) if not o.get('weapons') or w in o['weapons']]):add(f,w,c['key'],id)
from collections import Counter
summary={f:dict(Counter(x['status'] for x in rows if x['family']==f)) for f in ['firearm','bow','staff','melee','tool']}
out=Path('SourceAssets/BowFramedIcons20260930/coverage.json');out.write_text(json.dumps({'summary':summary,'rows':rows},indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(summary))
print('Firearm gaps:',json.dumps([x['key'] for x in rows if x['family']=='firearm' and x['status']!='framed']))
for f in ['staff','melee','tool']:
 print(f,'sample:',next((x['resolved'] for x in rows if x['family']==f and x['resolved']),None))
