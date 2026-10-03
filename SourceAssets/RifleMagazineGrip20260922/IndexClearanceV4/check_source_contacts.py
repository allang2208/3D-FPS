"""Report only the index/magazine contact frames requested for diagnosis."""
from pathlib import Path
import json,numpy as np
O=Path(__file__).parent
code=(O/'author_index.py').read_text().split('result={};report={}')[0]
exec(compile(code,str(O/'author_index.py'),'exec'))
poses=json.loads((O/'source_pose_samples.json').read_text());shells={k:Shell(v) for k,v in data['magazines'].items()}
result={}
for key,rows in poses.items():
    gun,magazine,_,_=key.split('/')
    mags=[gun,gun+'_extended'] if gun=='A762' else [gun+('_extended' if magazine=='extended' else '')]
    values={}
    for f,row in rows.items():
        skin=sum((bound[n]@np.array(row[n]).T)[:,:3]*weights[:,i,None] for i,n in enumerate(names))
        pts=samples(skin)
        values[f]={m:round(float(shells[m].clearance(pts).min()),4) for m in mags}
    result[key]=values
(O/'source_contact_diagnosis.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
for key,rows in result.items():
    worst=min((v,float(f),m) for f,vals in rows.items() for m,v in vals.items())
    print('SOURCE_INDEX_CLEARANCE',key,'worst_mm_frame_mag',worst,'hold',rows.get('148.0',rows.get('148')),flush=True)
