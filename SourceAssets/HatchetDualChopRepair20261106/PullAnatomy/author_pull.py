import json,sys
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P.parent))
from author import world
from pull_arm import repair_pull
report={}
for label in ('Jason','Kaitlin'):
    data=json.loads((P/(label+'-source.json')).read_text());out=dict(mesh=data['mesh'],names=data['names'],fps=60,clips={});rows={};poses=[];labels=[]
    for role,clip in data['clips'].items():
        old=np.array(clip['frames']);new,metrics=repair_pull(old,data,role=='DualRelease')
        a=np.array([world(f,data['parents']) for f in old]);b=np.array([world(f,data['parents']) for f in new])
        hands=[data['names'].index('hand_'+s) for s in ('r','l')]
        metrics['max_hand_position_change_cm']=float(np.linalg.norm(a[:,hands,:3]-b[:,hands,:3],axis=2).max())
        metrics['max_hand_orientation_dot_error']=float(abs(abs((a[:,hands,3:7]*b[:,hands,3:7]).sum(2))-1).max())
        metrics['before_pull_max_translation_scale_change']=float(abs(old[:42,:,[0,1,2,7,8,9]]-new[:42,:,[0,1,2,7,8,9]]).max())
        metrics['before_pull_max_rotation_dot_error']=float(abs(abs((old[:42,:,3:7]*new[:42,:,3:7]).sum(2))-1).max())
        rows[role]=metrics;out['clips'][role]=new.round(9).tolist()
        for t in [.65,.70,.75,.82,1.0,1.13,1.3,1.48]:
            poses.append(b[round(t*60)]);labels.append(role+'_'+f'{t:.2f}')
    report[label]=rows;(P/(label+'-moves.json')).write_text(json.dumps(out,separators=(',',':')),'utf8')
    np.savez_compressed(P/(label+'-render.npz'),names=data['names'],poses=poses,labels=labels)
(P/'author-receipt.json').write_text(json.dumps(report,indent=2),'utf8');print(json.dumps(report,indent=2))
