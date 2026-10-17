"""Summarize the explicitly requested offline arm-direction investigation."""
import json
from pathlib import Path
import numpy as np

root=Path(__file__).resolve().parents[2]
out=root/'SourceAssets/WarhammerCastArm20261017/DirectionV2'
data=json.loads((out/'native-graph-diagnosis.json').read_text(encoding='utf-8-sig'))
rows=[]
for case in data['cases']:
    row={k:v for k,v in case.items() if k!='samples'}
    row['phases']={}
    for phase in ('Gather','Hold','Ready','Release','Recover'):
        samples=[s for s in case['samples'] if s['phase']==phase]
        last=samples[-1]
        row['phases'][phase]={k:round(last[k],4) for k in ('wrist_front_cm','elbow_front_cm')}
    for name in ('upper_length_cm','lower_length_cm'):
        values=[s[name] for s in case['samples']]
        row[name+'_range']=[min(values),max(values)]
    row['nonfinite_values']=sum(not np.isfinite(v) for s in case['samples'] for b in s['component_pose'].values() for v in b)
    rows.append(row)
summary={'kind':data['kind'],'rows':rows,'gameplay_or_multiplayer_acceptance':False}
(out/'native-graph-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
for row in rows:
    print(json.dumps(row,ensure_ascii=False))
