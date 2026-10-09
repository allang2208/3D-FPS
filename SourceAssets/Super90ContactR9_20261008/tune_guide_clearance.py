from pathlib import Path
O=Path(__file__).parent
exec(compile((O/'collision_core.py').read_text(),str(O/'collision_core.py'),'exec'))
rows=[]
for side in (.08,.085,.09,.10):
 for z in (-.03,-.035,-.04,-.045):
  s['PLUNGER_SIDE']=side;s['PLUNGER_STANDOFF']=z;s['pose_cache'].clear();hits=0
  for f in (87,100,113,114,115,120,126):
   p=s['pose'](f,7,False)[0];c=collision(p);hits+=sum(v['count'] for d in c.values() for v in d.values())
  rows.append({'side':side,'z':z,'hits':hits,'score':hits*100+((side-.08)**2+(z+.03)**2)*1e6})
rows.sort(key=lambda r:r['score']);print('GUIDE_CLEARANCE',rows[:5],flush=True);(O/'Diagnostics/guide_fit_candidates.json').write_text(json.dumps(rows,indent=2))
