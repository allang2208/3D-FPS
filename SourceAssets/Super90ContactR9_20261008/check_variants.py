from pathlib import Path
O=Path(__file__).parent
exec(compile((O/'collision_core.py').read_text(),str(O/'collision_core.py'),'exec'))
out={'checked_frames':0,'clips':[],'failures':[]}
for family in ('base','vertical','canted','prism','angled'):
 for empty in (False,True):
  prefix={}
  for count in (7,1,2,3,4,5,6):
   bad=0;checked=0;end=s['last_frame'](count)
   for f in range(s['duration'](count,empty)+1):
    if count!=7 and f<=end:r=prefix[f]
    else:
     p=s['pose'](f,count,empty,family)[0];r=collision(p,74<=f<end+13);out['checked_frames']+=1;checked+=1
    if count==7:prefix[f]=r
    hits=sum(v['count'] for d in r.values() for v in d.values())
    if hits:
     bad+=1;out['failures'].append({'family':family,'empty':empty,'count':count,'frame':f,'collision':r})
   out['clips'].append({'family':family,'empty':empty,'count':count,'failing_frames':bad,'unique_frames':checked});print('CONTACT_VARIANT',family,empty,count,'bad',bad,flush=True)
  (O/'Diagnostics/variant_contact.json').write_text(json.dumps(out,indent=2))
print('CONTACT_COMPLETE',out['checked_frames'],len(out['failures']),flush=True)
