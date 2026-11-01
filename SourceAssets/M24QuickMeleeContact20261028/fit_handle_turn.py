from pathlib import Path
exec(compile((Path(__file__).parent/'author_regrip.py').read_text().split('\nkeys=')[0],'grip','exec'))
results=[]
for angle in range(-180,181,15):
 q=Quaternion((0,0,1),math.radians(angle));pivot=Vector((0,.005,.045));Ds=Matrix.LocRotScale(pivot-q@Vector((0,0,.04)),q,Vector((1,1,1)));club={n:Ds@m for n,m in native.items() if under(n,'hand_r')};best=[]
 for t in (.14,.20,.25,.325,.4,.45):
  row=regrip(pose('quick_melee',t)[0],t);candidates=[]
  for off in ((0,0,0),(0,0,-3),(3,0,-3),(0,3,-3),(3,3,-6)):
   for phi in range(-150,151,10):
    value=solve(row,off,phi)
    if value:candidates.append(value)
  best.append(min(candidates,key=lambda v:v['score']))
 cost=sum(v['score'] for v in best)/len(best)+.0002*angle**2
 results.append({'angle':angle,'cost':cost,'max_bend':max(v['bend'] for v in best),'max_pen':max(max(v['capsule_penetration_cm']) for v in best),'samples':best});print('HANDLE',angle,cost,results[-1]['max_bend'],flush=True)
(O/'handle_turn_candidates.json').write_text(json.dumps(results,indent=2));print('BEST',json.dumps(min(results,key=lambda v:v['cost'])),flush=True)
