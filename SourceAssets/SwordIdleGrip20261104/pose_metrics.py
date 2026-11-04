from pathlib import Path
import json,numpy as np
from fit_math import *
P=Path(__file__).resolve().parent
length_error=0.;count=0
for path in (P/'After').glob('*/surface.json'):
    after=json.loads(path.read_text(encoding='utf-8-sig'));before=json.loads((P/'Before'/path.parent.name/'surface.json').read_text(encoding='utf-8-sig'))
    for a,b in zip(after['frames'],before['frames']):
        count+=1
        for s in ['r','l']:
            for first,last in [('upperarm','lowerarm'),('lowerarm','hand')]:
                def length(row):return np.linalg.norm(np.array(row['bones'][last+'_'+s]['p'])-row['bones'][first+'_'+s]['p'])
                length_error=max(length_error,abs(length(a)-length(b))*10)
charge={}
for variant,grip in [('Standard','factory'),('LongGrip','long_twohand')]:
    d=json.loads((P/'ChargeAfter'/variant/'surface.json').read_text(encoding='utf-8-sig'));idle=json.loads((P/'After'/('ue_frost_crystal_sword__'+grip+'__factory')/'surface.json').read_text(encoding='utf-8-sig'))['frames'][0]
    stats={}
    for label,row in [('start',d['frames'][0]),('end',d['frames'][-1])]:
        distances=[];angles=[]
        for n in ['hand_r','hand_l','thumb_01_r','thumb_02_r','thumb_01_l']:
            a=np.linalg.inv(matrix(row['weapon']))@matrix(row['bones'][n]);b=np.linalg.inv(matrix(idle['weapon']))@matrix(idle['bones'][n]);distances.append(float(np.linalg.norm(a[:3,3]-b[:3,3])*10));angles.append(float(np.linalg.norm(R.from_matrix(rotation(a).T@rotation(b)).as_rotvec())*180/np.pi))
        stats[label]={'max_mm':max(distances),'max_degrees':max(angles)}
    stats['samples']=len(d['frames']);charge[variant]=stats
contacts=json.loads((P/'after-contacts.json').read_text())
solid_cases=sum(any(value['count'] for side in row['contacts'].values() for name,value in side.items() if name!='grip') for row in contacts)
result={'weapons':6,'weapon_grip_pairs':34,'grip_guard_cases':len(contacts),'idle_frames':count,'max_bone_length_error_mm':length_error,'cases_with_guard_blade_pommel_or_other_hand_penetration_over_0_5mm':solid_cases,'charge_handoff':charge,'grip_contact_measurements':'Kept separately in after-contacts.json; authored grip contact is not a zero-intersection assertion.','runtime_gameplay_started':False}
(P/'pose-metrics.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
