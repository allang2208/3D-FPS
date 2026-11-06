import json,sys,shutil
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent;TASK=P.parent
sys.path.insert(0,str(TASK))
from author import world,ease,continuous
from elbow_skin import fit_elbow_skin
report={}
for label in ('Jason','Kaitlin'):
    source=json.loads((TASK/(label+'-source.json')).read_text())
    original=P/'Inputs'/(label+'-moves.json');original.parent.mkdir(exist_ok=True)
    if not original.exists():shutil.copy2(TASK/(label+'-moves.json'),original)
    data=json.loads(original.read_text());rows={};poses=[];labels=[];anchor=None
    for role,keys in data['clips'].items():
        old=np.array(keys);ts=np.arange(len(old))/60
        weights=ease(ts/.36) if role=='DualCharge' else 1-ease((ts-68/60)/(28/60)) if role=='DualRelease' else ease(ts/.36)*(1-ease((ts-.82)/1.03))
        new,next_anchor=fit_elbow_skin(old,source,weights,anchor if role=='DualRelease' else None)
        if role=='DualCharge':anchor=next_anchor
        new=continuous(new)
        ids=[source['names'].index(k+'_'+s) for s in ('r','l') for k in ('upperarm','lowerarm','hand')]
        wa=np.array([world(f,source['parents']) for f in old]);wb=np.array([world(f,source['parents']) for f in new])
        rows[role]=dict(primary_chain_position_change_cm=float(np.linalg.norm(wa[:,ids,:3]-wb[:,ids,:3],axis=2).max()),
            primary_chain_rotation_dot_error=float(abs(abs((wa[:,ids,3:7]*wb[:,ids,3:7]).sum(2))-1).max()),
            scale_change=float(abs(old[:,:,7:]-new[:,:,7:]).max()))
        data['clips'][role]=new.round(9).tolist()
        times=[1.,2.] if role=='DualCharge' else [0,.12,.24,.38,.75,1.12,1.6] if role=='DualRelease' else [.36,.60,.82]
        for t in times:
            poses.append(world(new[round(t*60)],source['parents']));labels.append(role+'_'+f'{t:.2f}')
    np.savez_compressed(P/(label+'-render.npz'),names=source['names'],poses=poses,labels=labels)
    (P/(label+'-moves.json')).write_text(json.dumps(data,separators=(',',':')),'utf8');report[label]=rows
(P/'author-receipt.json').write_text(json.dumps(report,indent=2),'utf8')
print(json.dumps(report,indent=2))
