from pathlib import Path
O=Path(__file__).parent
exec(compile((O/'collision_core.py').read_text(),str(O/'collision_core.py'),'exec'))
rows=[];poses={(empty,f):s['pose'](f,7,empty)[0] for empty in (False,True) for f in (121,123,125,126)}
for side in (-2.,-1.,0.,1.,2.):
 for front in (-1.,0.,1.):
  total=0
  for (empty,f),base in poses.items():
   p={n:m.copy() for n,m in base.items()};drop=(f-120)/(60*.85);delta=s['right']*((side-.08)*drop)+s['forward']*(front*drop)
   for n in ('WPN_Shell','WPN_SOCKET_Magazine'):p[n].translation+=delta
   c=collision(p);total+=sum(c[hand]['props']['count'] for hand in c)
  rows.append({'side':side,'forward':front,'count':total,'score':total*100+side*side+front*front})
rows.sort(key=lambda r:r['score']);(O/'Diagnostics/drop_fit.json').write_text(json.dumps(rows,indent=2));print('DROP',rows[:4],flush=True)
