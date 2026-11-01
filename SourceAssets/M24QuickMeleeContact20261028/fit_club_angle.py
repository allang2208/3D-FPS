from pathlib import Path
exec(compile((Path(__file__).parent/'author_regrip.py').read_text().split('\nkeys=')[0],'grip','exec'))
baseclub={n:m.copy() for n,m in club.items()};results=[]
for angle in range(-150,151,15):
 spin=Quaternion((0,1,0),math.radians(angle));Ds=Matrix.LocRotScale(center1-spin@center1,spin,Vector((1,1,1)));club={n:Ds@m for n,m in baseclub.items()};allbest=[]
 for t in (.14,.20,.25,.325,.40,.45):
  old,_=pose('quick_melee',t);row=regrip(old,t);options=[]
  for off in ((0,0,0),(0,0,-3),(3,0,-3),(0,3,-3),(3,3,-6)):
   for phi in range(-150,151,10):
    value=solve(row,off,phi)
    if value:options.append(value)
  if options:allbest.append(min(options,key=lambda v:v['score']))
 total=sum(d['score'] for d in allbest)/len(allbest)+.002*angle*angle if len(allbest)==6 else 1e6
 results.append({'angle':angle,'cost':total,'max_bend':max(d['bend'] for d in allbest),'max_pen':max(max(d['capsule_penetration_cm']) for d in allbest),'samples':allbest});print('ANGLE',angle,total,results[-1]['max_bend'],flush=True)
(O/'club_angle_candidates.json').write_text(json.dumps(results,indent=2));print('BEST',json.dumps(min(results,key=lambda v:v['cost'])),flush=True)
