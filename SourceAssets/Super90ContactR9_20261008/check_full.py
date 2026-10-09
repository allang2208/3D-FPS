from pathlib import Path
O=Path(__file__).parent
exec(compile((O/'collision_core.py').read_text(),str(O/'collision_core.py'),'exec'))
out=[]
for empty in (False,True):
 for f in range(s['duration'](7,empty)+1):
    p=s['pose'](f,7,empty)[0];col=collision(p,74<=f<127);hits=sum(v['count'] for a in col.values() for v in a.values())
    row={'frame':f,'empty':empty,'collision':col,'wrist_swing':wrist_swing(p,'l')};out.append(row)
    if hits:print('CONTACT',empty,f,hits,col,flush=True)
(O/'Diagnostics/full_contact.json').write_text(json.dumps(out,indent=2))
print('FULL_CONTACT_COMPLETE',len(out),flush=True)
