"""Scoped native-data checks for the requested throw-exit diagnosis."""
import json, math
from pathlib import Path
from mathutils import Quaternion,Vector,Matrix
P=Path(__file__).resolve().parent
before=json.loads((P/'native-poses-before.json').read_text());after=json.loads((P/'native-poses.json').read_text())
def q(t):return Quaternion((t[6],t[3],t[4],t[5])).normalized()
def angle(a,b):
    v=math.degrees(q(a).rotation_difference(q(b)).angle);return min(v,360-v)
def error(a,b,indices):
    return {'position_cm':max(math.dist(x[i][:3],y[i][:3]) for x,y in zip(a,b) for i in indices),
            'rotation_deg':max(angle(x[i],y[i]) for x,y in zip(a,b) for i in indices)}
checks=[]
def check(name,value):checks.append({'check':name,**value,'pass':value['position_cm']<.002 and value['rotation_deg']<.06})
names=after['Release']['names'];count=len(names)
check('charge remains V6',error(before['Charge']['frames'],after['Charge']['frames'],range(count)))
check('weapon drive unchanged',error(before['Release']['frames'],after['Release']['frames'],[names.index('WPN_root')]))
check('throw through .24 unchanged',error(before['Release']['frames'][:58],after['Release']['frames'][:58],range(count)))
check('original endpoint retained',error(before['Release']['frames'][-1:],after['Release']['frames'][-1:],range(count)))
comparison={}
for label,d in [('before',before),('after',after)]:
    f=d['Release']['frames'];fps=d['Release']['fps'];details={}
    for s in ('l','r'):
        u,l,h=[names.index(n+'_'+s) for n in ('upperarm','lowerarm','hand')]
        def speed(i):return math.dist(f[i-1][h][:3],f[i+1][h][:3])*fps/2
        lengths=[[math.dist(frame[i][:3],frame[j][:3]) for frame in f] for i,j in [(u,l),(l,h)]]
        details[s]={'hand_speed_at_315_cm_s':speed(round(.315*fps)),
                    'late_peak_hand_speed_cm_s':max(speed(i) for i in range(round(.65*fps),len(f)-1)),
                    'post_release_max_hand_frame_step_cm':max(math.dist(f[i-1][h][:3],f[i][h][:3]) for i in range(58,len(f))),
                    'bone_length_variation_cm':max(max(v)-min(v) for v in lengths)}
    comparison[label]=details
for side,values in comparison['after'].items():
    checks.append({'check':side+' no sudden post-release wrist jump','pass':values['post_release_max_hand_frame_step_cm']<2.0,
                   'maximum_frame_step_cm':values['post_release_max_hand_frame_step_cm']})
report={'checks':checks,'failed':sum(not v['pass'] for v in checks),'comparison':comparison,
        'reader':'actual saved native sequence data model','gameplay_run':False,'offline_surface_excludes_runtime_corrective_morphs':True}
(P/'review-receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report),flush=True)
