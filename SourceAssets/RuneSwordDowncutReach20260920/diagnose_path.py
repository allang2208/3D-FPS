import json,math
from pathlib import Path
P=Path(__file__).parent
def sub(a,b):return [x-y for x,y in zip(a,b)]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def length(a):return math.sqrt(dot(a,a))
def angle(a,b):return math.degrees(math.acos(max(-1,min(1,dot(a,b)/(length(a)*length(b))))))
result={}
for variant in ('Standard','LongGrip'):
 data=json.loads((P/(variant+'_input.json')).read_text());rows=[]
 for row in data['samples']:
  t=row['seconds']
  if not 1.1<=t<=1.75:continue
  metric={'time':t,'sides':{}}
  for side in ('l','r'):
   a,e,h=[row['world'][n+'_'+side]['p'] for n in ('upperarm','lowerarm','hand')]
   metric['sides'][side]={'elbow_interior_deg':angle(sub(a,e),sub(h,e)),'wrist_forward_cm':-h[1],'wrist_height_cm':h[2],'shoulder_forward_cm':-a[1],'shoulder_height_cm':a[2]}
  rows.append(metric)
 result[variant]={'descent_min':{s:min(r['sides'][s]['elbow_interior_deg'] for r in rows if r['time']<=1.31) for s in ('l','r')},'rows':rows}
(P/'before_path_diagnosis.json').write_text(json.dumps(result,indent=2))
for variant,data in result.items():
 print(variant,'descent_min',data['descent_min'])
 for target in (1.11,1.20,1.24,1.27,1.31,1.50):
  print(min(data['rows'],key=lambda r:abs(r['time']-target)))
