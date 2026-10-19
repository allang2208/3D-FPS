"""Requested follow-up: full second-cut hand continuity and unchanged bone lengths."""
import json,math
from pathlib import Path
P=Path(__file__).resolve().parent;V1=P.parent/'ChixiaoDoubleHeavyV1'
env={'__file__':str(V1/'author_motion.py')}
exec(compile((V1/'author_motion.py').read_text('utf-8').split('receipt=')[0],str(V1/'author_motion.py'),'exec'),env)
A=env['A'];out={}
for variant in ('Standard','LongGrip'):
    source=json.loads((V1/variant/'editable_keys.json').read_text('utf-8'));fixed=json.loads((P/variant/'editable_keys.json').read_text('utf-8'))
    rest=A.pose_from_rows(source['samples'][-1]['bones']);lengths={s:[(rest['lowerarm_'+s].translation-rest['upperarm_'+s].translation).length,
        (rest['hand_'+s].translation-rest['lowerarm_'+s].translation).length] for s in ('l','r')}
    result={'first_cut_identical':all(a['bones']==b['bones'] for a,b in zip(source['samples'],fixed['samples']) if a['seconds']<=.12),
        'hand_shapes':{},'max_bone_length_error_cm':0.,'recovery_hand_step_cm':{},'end_hand_step_cm':{}}
    previous=None
    for sample in fixed['samples']:
        w=A.pose_from_rows(sample['bones']);t=sample['seconds']
        for s in ('l','r'):
            u,l,h=[w[n+'_'+s].translation for n in ('upperarm','lowerarm','hand')]
            result['max_bone_length_error_cm']=max(result['max_bone_length_error_cm'],abs((l-u).length-lengths[s][0])*100,abs((h-l).length-lengths[s][1])*100)
            if previous and t>=.38:
                step=(h-previous['hand_'+s].translation).length*100
                if step>result['recovery_hand_step_cm'].get(s,{}).get('value',-1):result['recovery_hand_step_cm'][s]={'t':t,'value':step}
                if t>=1.:result['end_hand_step_cm'][s]=step
        previous=w
    out[variant]=result
(P/'continuity-check.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out),flush=True)
