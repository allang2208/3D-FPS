from pathlib import Path
O=Path(__file__).parent
exec(compile((O/'saved_collision_core.py').read_text(),str(O/'saved_collision_core.py'),'exec'))
data=json.loads((O/'Diagnostics/saved_assets.json').read_text());ni={n:i for i,n in enumerate(data['names'])};out={'checked_frames':0,'failures':[]}
for name,clip in data['clips'].items():
 count=int(name[-1]) if not name.endswith('cycle') else 0
 for row in clip['rows']:
  world={}
  for n in names:world[n]=world.get(s['parents'][n],Matrix.Identity(4))@s['uemat'](row['local'][ni[n]])
  p={n:s['evaluation_to_author']@s['Ci']@world[n]@s['Ki'][n] for n in names};f=row['frame'];c=collision(p,count>0 and 74<=f<s['last_frame'](count)+13);out['checked_frames']+=1
  if any(v['count'] for d in c.values() for v in d.values()):out['failures'].append({'clip':name,'frame':f,'collision':c})
 print('SAVED_COLLISION',name,flush=True)
(O/'Diagnostics/saved_collision.json').write_text(json.dumps(out,indent=2));print('SAVED_CONTACT',out['checked_frames'],len(out['failures']),flush=True)
