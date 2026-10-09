from pathlib import Path
O=Path(__file__).parent
exec(compile((O/'collision_core.py').read_text(),str(O/'collision_core.py'),'exec'))
out=[]
for f in range(67):
 p=s['cycle_pose'](f)
 c=collision(p,False);hits=sum(v['count'] for d in c.values() for v in d.values())
 if hits:out.append({'frame':f,'collision':c})
(O/'Diagnostics/cycle_contact.json').write_text(json.dumps(out,indent=2));print('CYCLE',out,flush=True)
