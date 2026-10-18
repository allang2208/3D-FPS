import sys,json
from pathlib import Path
import numpy as np
O=Path(__file__).parent;R=O.parents[1];sys.path.insert(0,str(R/'SourceAssets/LambGripV8_20261017'))
import pose_model as P
before=json.loads((O/'Before/Content/ColdSteelData/potion_use_motion.json').read_text(encoding='utf-8'))['roasted_large_lamb'];after=P.data['roasted_large_lamb'];report={}
for label,m in [('before',before),('after',after)]:
    rows=[]
    for t in np.linspace(m['times']['drink_end'],m['times']['release'],54):
        _,obj,pose,info=P.solve(m,float(t),False)
        rows.append(dict(time=float(t),left=list(pose['hand_l'].translation),right=list(pose['hand_r'].translation)))
    report[label]=dict(samples=rows,forward_retreat_cm={s:max(r[s][0] for r in rows)-min(r[s][0] for r in rows) for s in ['left','right']},downward_distance_cm={s:rows[0][s][2]-rows[-1][s][2] for s in ['left','right']},monotonic_down={s:all(b[s][2]<=a[s][2]+1e-4 for a,b in zip(rows,rows[1:])) for s in ['left','right']})
report['unchanged']=dict(times=before['times']==after['times'],grip=all(before[k]==after[k] for k in ['digits','right_digits','grip_in_palm','right_grip_in_palm','palm_rotation','right_palm_rotation']))
(O/'fps_exit_review.json').write_text(json.dumps(report,indent=2))
print({k:{n:v for n,v in r.items() if n!='samples'} for k,r in report.items()})
