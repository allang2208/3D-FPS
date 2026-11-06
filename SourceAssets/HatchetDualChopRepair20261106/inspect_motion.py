"""Focused numeric diagnosis of edited arm chains and combo boundary poses."""
import json
from pathlib import Path
import numpy as np
from author import world,sample

P=Path(__file__).resolve().parent
result={}
for label in ('Jason','Kaitlin'):
    source=json.loads((P/(label+'-source.json')).read_text())
    edited=json.loads((P/(label+'-moves.json')).read_text())
    names=source['names'];parents=source['parents']
    hands=[names.index('hand_'+s) for s in ('r','l')]
    joints=[names.index(k+'_'+s) for s in ('r','l') for k in ('upperarm','upperarm_twist_02','lowerarm','lowerarm_twist_01','lowerarm_twist_02','hand')]
    rows={}
    for role,keys in edited['clips'].items():
        frames=np.array(keys);qs=frames[:,joints,3:7]
        step=2*np.degrees(np.arccos(np.clip(abs((qs[1:]*qs[:-1]).sum(2)),0,1)))
        row=dict(seconds=(len(frames)-1)/60,max_local_rotation_step_deg=float(step.max()))
        if role in source['clips']:
            original=np.array(source['clips'][role]['frames']);drift=0.
            for i in range((len(frames)-1)*2+1):
                a=world(sample(original,i/120),parents)[hands,:3]
                b=world(sample(frames,i/120),parents)[hands,:3]
                drift=max(drift,float(np.linalg.norm(a-b,axis=1).max()))
            row['max_120hz_hand_drift_cm']=drift
        rows[role]=row
    def delta(a,b):
        wa,wb=world(a,parents),world(b,parents)
        return dict(hand_position_cm=float(np.linalg.norm(wa[hands,:3]-wb[hands,:3],axis=1).max()),
            arm_rotation_deg=float((2*np.degrees(np.arccos(np.clip(abs((wa[joints,3:7]*wb[joints,3:7]).sum(1)),0,1)))).max()))
    frames={k:np.array(v) for k,v in edited['clips'].items()}
    rows['charge_release_join']=delta(frames['DualCharge'][-1],frames['DualRelease'][0])
    rows['combo_entry']=delta(np.array(source['clips']['Attack2']['frames'][-1]),frames['Combo3'][0])
    rows['combo_exit']=delta(frames['Combo3'][-1],np.array(source['clips']['Idle']['frames'][0]))
    result[label]=rows
(P/'motion-diagnosis.json').write_text(json.dumps(result,indent=2),'utf8')
print(json.dumps(result,indent=2))
