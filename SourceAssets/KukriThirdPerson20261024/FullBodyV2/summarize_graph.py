"""Assess the requested native pose matrix, not compilation or file existence."""
import json,math,statistics
from pathlib import Path
OUT=Path(__file__).resolve().parent
data=json.loads((OUT/'native-graph-after.json').read_text(encoding='utf-8-sig'))
rows=data['rows'];failures=list(data['errors']);indexed={}
attacks={'Slash1','Slash2','Thrust','Heavy','Dash','Uppercut','Pommel','Whirlwind.Loop'}
def span(r,side):return math.sqrt(sum(v*v for v in r[side+'_ankle_range']))
for r in rows:
    key=(r['body'],r['role'],r['scenario']);indexed[key]=r
    if not r['finite']:failures.append(str(key)+': nonfinite pose')
    if '/FullBodyV2/' not in r['asset']:failures.append(str(key)+': old runtime route')
    if r['scenario']=='stand' and r['role'] in attacks:
        if max(span(r,'left'),span(r,'right'))<5:failures.append(str(key)+': attack has no effective footstep')
        if min(r['left_flex_min'],r['right_flex_min'])<8:failures.append(str(key)+': knee collapses to near-straight')
    if r['role']=='Whirlwind.Loop' and r['scenario']=='stand':
        if min(span(r,'left'),span(r,'right'))<5:failures.append(str(key)+': turning foot remains frozen')
    if r['scenario']=='run' and max(span(r,'left'),span(r,'right'))<15:
        failures.append(str(key)+': running legs remain frozen')
for (body,role,scenario),r in indexed.items():
    if scenario!='crouch':continue
    standing=indexed[(body,role,'stand')]
    z=statistics.median(s['pelvis'][2] for s in r['samples'])
    stand_z=statistics.median(s['pelvis'][2] for s in standing['samples'])
    if stand_z-z<20:failures.append(str((body,role))+': crouched attack loses hip lowering')
summary=dict(rows=len(rows),bodies=sorted({r['body'] for r in rows}),roles=sorted({r['role'] for r in rows}),
    scenarios=sorted({r['scenario'] for r in rows}),failures=failures,
    standing_attacks=[{k:v for k,v in r.items() if k!='samples'} for r in rows if r['scenario']=='stand' and r['role'] in attacks],
    scope=data['scope'])
(OUT/'native-graph-summary.json').write_text(json.dumps(summary,indent=2))
print('native rows',len(rows),'failures',len(failures))
for f in failures:print(f)
for r in summary['standing_attacks']:
    print(r['body'],r['role'],'knee minima',round(r['right_flex_min'],1),round(r['left_flex_min'],1),
          'foot range norm',round(span(r,'right'),1),round(span(r,'left'),1))
if failures:raise SystemExit(1)
