from pathlib import Path
import json,math
R=Path(__file__).resolve().parent
m=json.loads((R/'repaired_manifest.json').read_text());count=0
for row in m['rows']:
 if 'SM_StreetLamp_A_Pole_Large' not in row['mesh']:continue
 keep=[]
 for t in row['transforms']:
  if math.dist(t['p'][:2],[46185.592903357596,-49904.443989009014])<.1:count+=1
  else:keep.append(t)
 row['transforms']=keep
if count!=1:raise RuntimeError('Expected exactly one isolated carriageway lamp')
m['counts']['instances']-=count
(R/'repaired_manifest.json').write_text(json.dumps(m,separators=(',',':')))
(R.parent/'publish_manifest.json').write_text(json.dumps(m,separators=(',',':')))
p=json.loads((R/'repair_plan.json').read_text());p['isolated_carriageway_lamp_removed']=count;p['final_manifest_instances']=m['counts']['instances'];(R/'repair_plan.json').write_text(json.dumps(p,indent=2))
print('REMOVED_ROAD_LAMP',count)
