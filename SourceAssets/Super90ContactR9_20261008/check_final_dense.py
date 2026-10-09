from pathlib import Path
O=Path(__file__).parent
exec(compile((O/'collision_core.py').read_text(),str(O/'collision_core.py'),'exec'))
out={'checked_samples':0,'failures':[]}
for family in ('base','vertical','canted','prism','angled'):
 for empty in (False,True):
  for count in range(1,8):
   begin=s['last_frame'](count)+(45 if empty else 8)
   for k in range(begin*2,s['duration'](count,empty)*2+1):
    f=k/2;p=s['pose'](f,count,empty,family)[0];c=collision(p,74<=f<s['last_frame'](count)+13);out['checked_samples']+=1
    if any(v['count'] for d in c.values() for v in d.values()):out['failures'].append({'family':family,'empty':empty,'count':count,'frame':f,'collision':c})
 for k in range(133):
  f=k/2;p=s['cycle_pose'](f,family);c=collision(p,False);out['checked_samples']+=1
  if any(v['count'] for d in c.values() for v in d.values()):out['failures'].append({'family':family,'cycle':True,'frame':f,'collision':c})
 (O/'Diagnostics/final_dense_contact.json').write_text(json.dumps(out,indent=2));print('DENSE_FAMILY',family,'failures',len(out['failures']),flush=True)
print('DENSE_DONE',out['checked_samples'],len(out['failures']),flush=True)
