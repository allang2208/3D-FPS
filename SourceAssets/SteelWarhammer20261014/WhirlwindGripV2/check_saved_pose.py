"""Compare the saved UE source/compressed poses for the requested grip check."""
import json,math
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
P=Path(__file__).resolve().parent
data=json.loads((P/'saved_pose_samples.json').read_text())
def matrix(row):return Matrix.LocRotScale(Vector(row['p']),Quaternion(row['q']),Vector(row['s']))
def angle(a,b):return math.degrees(2*math.acos(min(1.,abs(a.normalized().dot(b.normalized())))))
metrics={}
for kind,rows in data.items():
    first={n:matrix(v) for n,v in rows[0]['world'].items()}
    grip={s:first['WPN_root'].inverted()@first['hand_'+s] for s in ('l','r')}
    out={'samples':len(rows),'grip_position_error_mm':0.,'grip_rotation_error_degrees':0.,'bone_length_error_mm':0.,'min_hand_spacing_cm':1000.,'max_hand_spacing_cm':0.}
    for row in rows:
        pose={n:matrix(v) for n,v in row['world'].items()};wp=pose['WPN_root']
        gap=(pose['hand_l'].translation-pose['hand_r'].translation).length
        out['min_hand_spacing_cm']=min(out['min_hand_spacing_cm'],gap);out['max_hand_spacing_cm']=max(out['max_hand_spacing_cm'],gap)
        for s in ('l','r'):
            expected=wp@grip[s];hand=pose['hand_'+s]
            out['grip_position_error_mm']=max(out['grip_position_error_mm'],10*(expected.translation-hand.translation).length)
            out['grip_rotation_error_degrees']=max(out['grip_rotation_error_degrees'],angle(expected.to_quaternion(),hand.to_quaternion()))
            for a,b in [('upperarm','lowerarm'),('lowerarm','hand')]:
                a+='_'+s;b+='_'+s
                out['bone_length_error_mm']=max(out['bone_length_error_mm'],10*abs((pose[a].translation-pose[b].translation).length-(first[a].translation-first[b].translation).length))
    out['pass']=out['grip_position_error_mm']<.5 and out['grip_rotation_error_degrees']<.15 and out['bone_length_error_mm']<.1
    metrics[kind]=out
error=0.
for a,b in zip(data['SOURCE'],data['COMPRESSED']):
    for n in a['world']:
        error=max(error,10*(Vector(a['world'][n]['p'])-Vector(b['world'][n]['p'])).length)
metrics['source_compressed_position_error_mm']=error
metrics['pass']=all(metrics[k]['pass'] for k in ('SOURCE','COMPRESSED')) and error<.2
metrics['runtime_tested']=False
(P/'saved_pose_check.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8');print(json.dumps(metrics))
if not metrics['pass']:raise RuntimeError('Saved animation contact check failed')
